"""OHLCV job — daily candle ingestion for index members."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from ..db.engine import get_engine
from ..repositories.job_run_repository import JobRunRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..fundamentals.repositories.instrument_query_repository import InstrumentQueryRepository
from ..ohlcv.providers.tradingview_provider import TradingViewOhlcvProvider
from ..ohlcv.providers.yfinance_provider import YfinanceOhlcvProvider
from ..ohlcv.providers.base import ProviderError
from ..ohlcv.normalize import normalize_ohlcv_df, NormalizationError
from ..ohlcv.repositories.ohlcv_repository import OhlcvRepository

logger = logging.getLogger(__name__)

# Default exchange when instrument has no exchange in DB
_DEFAULT_EXCHANGE = "NASDAQ"


class OhlcvJob:
    """Daily OHLCV ingestion job.

    Flow per ticker:
    1. Resolve exchange from ``instruments.exchange`` (fallback: config / NASDAQ).
    2. Try TradingView provider (primary).
    3. Fallback to yfinance on failure.
    4. Normalize the DataFrame.
    5. Upsert into ``ohlcv_daily``.
    6. Record ``job_run_item`` SUCCESS / FAILED.
    """

    REQUIRED_FIELDS = ("code", "country", "index_code", "timeframe")

    def __init__(
        self,
        engine=None,
        target_cfg: dict | None = None,
        global_cfg: dict | None = None,
    ):
        self.engine = engine or get_engine()
        self.target_cfg = target_cfg or {}
        self.global_cfg = global_cfg or {}
        self.job_run_repo = JobRunRepository(self.engine)
        self.job_run_item_repo = JobRunItemRepository(self.engine)
        self.instrument_query_repo = InstrumentQueryRepository(self.engine)
        self.ohlcv_repo = OhlcvRepository(self.engine)

    @classmethod
    def from_config(cls, target_cfg: dict, global_cfg: dict | None = None) -> "OhlcvJob":
        return cls(target_cfg=target_cfg, global_cfg=global_cfg)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        missing = [f for f in self.REQUIRED_FIELDS if f not in self.target_cfg]
        if missing:
            raise ValueError(f"OHLCV config missing required fields: {missing}")

    def resolve_date_window(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> tuple[date, date]:
        end = date.fromisoformat(to_date) if to_date else date.today()
        if from_date:
            start = date.fromisoformat(from_date)
        else:
            window_days = int(self.target_cfg.get("window_days", 400))
            start = end - timedelta(days=window_days)
        if start > end:
            raise ValueError(f"from_date ({start}) is after to_date ({end})")
        return start, end

    # ------------------------------------------------------------------
    # Instrument resolution
    # ------------------------------------------------------------------

    def _resolve_instruments(self, ticker: Optional[str], job_run_id: str) -> list[dict]:
        """Return list of dicts with keys: id, ticker, country, exchange."""
        country = self.target_cfg.get("country", "US")

        if ticker:
            inst = self.instrument_query_repo.get_instrument_by_ticker(ticker, country)
            if not inst:
                raise ValueError(
                    f"Ticker '{ticker}' not found in instruments for country={country}. "
                    "Run discovery first."
                )
            return [inst]

        index_code = self.target_cfg["index_code"]
        instruments = self.instrument_query_repo.get_instruments_for_index(
            index_code=index_code, country=country,
        )
        if not instruments:
            raise ValueError(
                f"No instruments found for index_code={index_code} country={country}. "
                "Run discovery first."
            )
        return instruments

    def _exchange_for(self, instrument: dict) -> str:
        """Resolve the exchange for a given instrument.

        Priority: instrument.exchange (DB) → NASDAQ default.
        """
        return instrument.get("exchange") or _DEFAULT_EXCHANGE

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        ticker: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> None:
        self._validate_config()
        start, end = self.resolve_date_window(from_date, to_date)
        limit = int(self.target_cfg.get("window_days", 400))

        job_run_id = self.job_run_repo.create(job_name="ohlcv", trigger_type="MANUAL_CLI")
        logger.info(
            "OHLCV job started — job_run_id=%s index=%s window=%s→%s ticker=%s",
            job_run_id,
            self.target_cfg.get("index_code"),
            start, end, ticker,
        )

        instruments = self._resolve_instruments(ticker, job_run_id)

        tv_provider = TradingViewOhlcvProvider()
        yf_provider = YfinanceOhlcvProvider()

        results: list[dict] = []
        succeeded = 0
        failed = 0

        for inst in instruments:
            t = inst["ticker"]
            exchange = self._exchange_for(inst)
            instrument_id = str(inst["id"])
            provider_used = ""
            row_count = 0
            min_date = ""
            max_date = ""
            status = "FAILED"

            try:
                # 1. Try TradingView
                raw_df = None
                try:
                    raw_df = tv_provider.fetch_daily(
                        exchange=exchange,
                        symbol=t,
                        start_date=str(start),
                        end_date=str(end),
                        limit=limit,
                    )
                    provider_used = "tradingview"
                except ProviderError as tv_err:
                    logger.warning(
                        "TradingView failed for %s:%s — falling back to yfinance: %s",
                        exchange, t, tv_err,
                    )
                    # 2. Fallback to yfinance
                    raw_df = yf_provider.fetch_daily(
                        exchange=exchange,
                        symbol=t,
                        start_date=str(start),
                        end_date=str(end),
                        limit=limit,
                    )
                    provider_used = "yfinance"

                # 3. Normalize
                clean_df = normalize_ohlcv_df(raw_df)

                # 4. Upsert
                row_count = self.ohlcv_repo.upsert_bulk(
                    instrument_id=instrument_id,
                    df=clean_df,
                    source=provider_used,
                    job_run_id=job_run_id,
                )

                min_date = str(clean_df["as_of_date"].min())
                max_date = str(clean_df["as_of_date"].max())
                status = "SUCCESS"

                self.job_run_item_repo.upsert(
                    job_run_id=job_run_id, item_key=t, status="SUCCESS",
                )
                succeeded += 1

            except Exception as exc:
                logger.error("OHLCV ticker=%s failed: %s", t, exc)
                try:
                    self.job_run_item_repo.upsert(
                        job_run_id=job_run_id,
                        item_key=t,
                        status="FAILED",
                        error_summary=str(exc),
                    )
                except Exception:
                    pass
                failed += 1

            results.append(
                {
                    "ticker": t,
                    "provider": provider_used,
                    "rows": row_count,
                    "min_date": min_date,
                    "max_date": max_date,
                    "status": status,
                }
            )

        # Finalize job run
        total = len(instruments)
        final_status = "FAILED" if failed > 0 else "SUCCESS"
        self.job_run_repo.finalize(
            job_run_id=job_run_id,
            status=final_status,
            items_total=total,
            items_succeeded=succeeded,
            items_failed=failed,
        )

        # CLI summary table
        self._print_summary(results, total, succeeded, failed)

    # ------------------------------------------------------------------
    # CLI summary
    # ------------------------------------------------------------------

    @staticmethod
    def _print_summary(
        results: list[dict], total: int, succeeded: int, failed: int,
    ) -> None:
        if results:
            df = pd.DataFrame(results)
            print(df.to_markdown(index=False), flush=True)
        print(
            f"\nTotal: {total}  Succeeded: {succeeded}  Failed: {failed}",
            flush=True,
        )
