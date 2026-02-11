"""OHLCV ingestion service — reusable orchestration for scheduled and backfill jobs."""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta

import pandas as pd

from ..db.engine import get_engine
from ..repositories.job_run_repository import JobRunRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..fundamentals.repositories.instrument_query_repository import (
    InstrumentQueryRepository,
)
from .providers.tradingview_provider import TradingViewOhlcvProvider
from .providers.yfinance_provider import YfinanceOhlcvProvider
from .providers.base import (
    ProviderEmptyError,
    TransientProviderError,
    PermanentProviderError,
)
from .normalize import normalize_ohlcv_df
from .reliability import retry_with_backoff
from .repositories.ohlcv_repository import OhlcvRepository

logger = logging.getLogger(__name__)

_DEFAULT_EXCHANGE = "NASDAQ"

REQUIRED_CFG_FIELDS = ("code", "country", "index_code", "timeframe")


def run_ohlcv_ingestion(
    *,
    target_name: str,
    cfg: dict,
    start_date: date,
    end_date: date,
    ticker: str | None = None,
    limit: int | None = None,
    chunk_days: int | None = None,
    skip_existing: bool = False,
    engine=None,
) -> dict:
    """Run OHLCV ingestion for an index target or a single ticker.

    This is the shared orchestration entry-point consumed by the scheduled
    OHLCV job and (in the future) the backfill job.

    Parameters
    ----------
    target_name : str
        Human-readable target label (e.g. ``nasdaq-100``).
    cfg : dict
        Already-loaded target config dict (keys: code, country,
        index_code, timeframe, window_days, default_exchange …).
    start_date, end_date : date
        Inclusive date window for candle fetching.
    ticker : str | None
        If given, ingest only this single ticker.
    limit : int | None
        Process at most *limit* tickers (for testing).
    chunk_days : int | None
        When provided and > 0, the requested date window is split into
        sequential sub-windows of *chunk_days* calendar days each.  The
        last chunk ends exactly at *end_date*.
    skip_existing : bool
        When ``True``, skip tickers whose existing DB coverage fully
        contains the requested ``[start_date, end_date]`` window.
    engine : sqlalchemy.Engine | None
        Optional engine override; falls back to ``get_engine()``.

    Returns
    -------
    dict
        Summary with keys: ``job_run_id``, ``target_name``, ``start_date``,
        ``end_date``, ``status``, ``total``, ``succeeded``, ``failed``,
        ``items`` (list of per-ticker result dicts).
    """
    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------
    missing = [f for f in REQUIRED_CFG_FIELDS if f not in cfg]
    if missing:
        raise ValueError(f"OHLCV config missing required fields: {missing}")

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------
    eng = engine or get_engine()
    job_run_repo = JobRunRepository(eng)
    job_run_item_repo = JobRunItemRepository(eng)
    instrument_query_repo = InstrumentQueryRepository(eng)
    ohlcv_repo = OhlcvRepository(eng)

    candle_limit = int(cfg.get("window_days", 400))
    default_exchange = cfg.get("default_exchange", _DEFAULT_EXCHANGE)

    job_run_id = job_run_repo.create(job_name="ohlcv", trigger_type="MANUAL_CLI")
    logger.info(
        "OHLCV ingestion started — job_run_id=%s target=%s window=%s→%s ticker=%s",
        job_run_id, target_name, start_date, end_date, ticker,
    )

    # ------------------------------------------------------------------
    # Instrument resolution
    # ------------------------------------------------------------------
    instruments = _resolve_instruments(instrument_query_repo, cfg, ticker)
    if limit is not None and limit > 0:
        instruments = instruments[:limit]
        logger.info("--limit applied: processing %d of total instruments", len(instruments))

    # ------------------------------------------------------------------
    # Providers (created once, reused across tickers)
    # ------------------------------------------------------------------
    tv_provider = TradingViewOhlcvProvider()
    yf_provider = YfinanceOhlcvProvider()

    # ------------------------------------------------------------------
    # Per-ticker ingestion loop
    # ------------------------------------------------------------------
    items: list[dict] = []
    succeeded = 0
    failed = 0

    for inst in instruments:
        result = _ingest_ticker(
            ticker=inst["ticker"],
            exchange=inst.get("exchange") or default_exchange,
            instrument_id=str(inst["id"]),
            start_date=start_date,
            end_date=end_date,
            candle_limit=candle_limit,
            tv_provider=tv_provider,
            yf_provider=yf_provider,
            ohlcv_repo=ohlcv_repo,
            job_run_id=job_run_id,
            job_run_item_repo=job_run_item_repo,
            skip_existing=skip_existing,
            chunk_days=chunk_days,
        )
        items.append(result)
        if result["status"] == "SUCCESS":
            succeeded += 1
        else:
            failed += 1

    # ------------------------------------------------------------------
    # Finalize job run
    # ------------------------------------------------------------------
    total = len(instruments)
    final_status = "FAILED" if failed > 0 else "SUCCESS"
    job_run_repo.finalize(
        job_run_id=job_run_id,
        status=final_status,
        items_total=total,
        items_succeeded=succeeded,
        items_failed=failed,
    )

    return {
        "job_run_id": job_run_id,
        "target_name": target_name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "status": final_status,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "items": items,
    }


# -----------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------

def _resolve_instruments(
    repo: InstrumentQueryRepository,
    cfg: dict,
    ticker: str | None,
) -> list[dict]:
    """Return instrument dicts (id, ticker, country, exchange)."""
    country = cfg.get("country", "US")

    if ticker:
        inst = repo.get_instrument_by_ticker(ticker, country)
        if not inst:
            raise ValueError(
                f"Ticker '{ticker}' not found in instruments for country={country}. "
                "Run discovery first."
            )
        return [inst]

    index_code = cfg["index_code"]
    instruments = repo.get_instruments_for_index(
        index_code=index_code, country=country,
    )
    if not instruments:
        raise ValueError(
            f"No instruments found for index_code={index_code} country={country}. "
            "Run discovery first."
        )
    return instruments


def _fetch_with_fallback(
    tv_provider: TradingViewOhlcvProvider,
    yf_provider: YfinanceOhlcvProvider,
    exchange: str,
    symbol: str,
    start: str,
    end: str,
    limit: int,
) -> tuple[pd.DataFrame, str, bool]:
    """Try TradingView with retries, fall back to yfinance.

    Returns ``(df, provider_name, fallback_used)``.
    """
    tv_label = f"TradingView:{exchange}:{symbol}"
    yf_label = f"yfinance:{symbol}"

    # 1. TradingView with retries
    try:
        df = retry_with_backoff(
            lambda: tv_provider.fetch_daily(
                exchange=exchange,
                symbol=symbol,
                start_date=start,
                end_date=end,
                limit=limit,
            ),
            label=tv_label,
        )
        return df, "tradingview", False
    except (TransientProviderError, ProviderEmptyError, PermanentProviderError) as tv_err:
        logger.warning(
            "TradingView failed for %s:%s — falling back to yfinance: %s",
            exchange, symbol, tv_err,
        )

    # 2. yfinance fallback with retries
    df = retry_with_backoff(
        lambda: yf_provider.fetch_daily(
            exchange=exchange,
            symbol=symbol,
            start_date=start,
            end_date=end,
            limit=limit,
        ),
        label=yf_label,
    )
    return df, "yfinance", True


def _compute_chunks(
    start_date: date,
    end_date: date,
    chunk_days: int | None,
) -> list[tuple[date, date]]:
    """Split ``[start_date, end_date]`` into sequential sub-windows.

    If *chunk_days* is ``None`` or <= 0, returns a single chunk spanning
    the full range.  Otherwise each chunk covers *chunk_days* calendar
    days (inclusive start, inclusive end).  The last chunk always ends
    exactly at *end_date*.
    """
    if not chunk_days or chunk_days <= 0:
        return [(start_date, end_date)]

    chunks: list[tuple[date, date]] = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _is_fully_covered(
    ohlcv_repo: OhlcvRepository,
    instrument_id: str,
    start_date: date,
    end_date: date,
) -> tuple[bool, date | None, date | None]:
    """Check whether DB already covers ``[start_date, end_date]``.

    Returns ``(covered, existing_min, existing_max)``.
    """
    existing_min, existing_max = ohlcv_repo.get_date_bounds(instrument_id)
    if (
        existing_min is not None
        and existing_max is not None
        and existing_min <= start_date
        and existing_max >= end_date
    ):
        return True, existing_min, existing_max
    return False, existing_min, existing_max


def _ingest_ticker(
    *,
    ticker: str,
    exchange: str,
    instrument_id: str,
    start_date: date,
    end_date: date,
    candle_limit: int,
    tv_provider: TradingViewOhlcvProvider,
    yf_provider: YfinanceOhlcvProvider,
    ohlcv_repo: OhlcvRepository,
    job_run_id: str,
    job_run_item_repo: JobRunItemRepository,
    skip_existing: bool = False,
    chunk_days: int | None = None,
) -> dict:
    """Ingest OHLCV data for a single ticker and return a result dict."""

    # ------------------------------------------------------------------
    # Skip-existing v1 — fully covered check
    # ------------------------------------------------------------------
    if skip_existing:
        covered, ex_min, ex_max = _is_fully_covered(
            ohlcv_repo, instrument_id, start_date, end_date,
        )
        if covered:
            details = {
                "status_reason": "skip_existing_fully_covered",
                "existing_min_date": str(ex_min),
                "existing_max_date": str(ex_max),
                "requested_start": str(start_date),
                "requested_end": str(end_date),
            }
            job_run_item_repo.upsert(
                job_run_id=job_run_id,
                item_key=ticker,
                status="SUCCESS",
                error_details=json.dumps(details),
            )
            logger.info(
                "OHLCV ticker=%s SKIPPED — fully covered %s→%s (requested %s→%s)",
                ticker, ex_min, ex_max, start_date, end_date,
            )
            return {
                "ticker": ticker,
                "status": "SUCCESS",
                "skipped": True,
                "provider_used": "-",
                "rows_written": 0,
                "requested_start": str(start_date),
                "requested_end": str(end_date),
                "min_written": "",
                "max_written": "",
                "chunks_attempted": 0,
                "chunks_succeeded": 0,
                "error": None,
            }

    # ------------------------------------------------------------------
    # Compute chunks
    # ------------------------------------------------------------------
    chunks = _compute_chunks(start_date, end_date, chunk_days)

    # ------------------------------------------------------------------
    # Per-chunk ingestion loop
    # ------------------------------------------------------------------
    total_rows = 0
    global_min: date | None = None
    global_max: date | None = None
    last_provider = ""
    chunks_attempted = 0
    chunks_succeeded = 0
    chunk_errors: list[str] = []

    for chunk_start, chunk_end in chunks:
        chunks_attempted += 1
        try:
            raw_df, prov, fallback_used = _fetch_with_fallback(
                tv_provider, yf_provider,
                exchange=exchange,
                symbol=ticker,
                start=str(chunk_start),
                end=str(chunk_end),
                limit=candle_limit,
            )

            clean_df = normalize_ohlcv_df(raw_df)

            rows = ohlcv_repo.upsert_bulk(
                instrument_id=instrument_id,
                df=clean_df,
                source=prov,
                job_run_id=job_run_id,
            )

            total_rows += rows
            last_provider = prov
            chunk_min = clean_df["as_of_date"].min()
            chunk_max = clean_df["as_of_date"].max()
            if global_min is None or chunk_min < global_min:
                global_min = chunk_min
            if global_max is None or chunk_max > global_max:
                global_max = chunk_max
            chunks_succeeded += 1

            logger.info(
                "OHLCV ticker=%s chunk %s→%s provider=%s rows=%d fallback=%s",
                ticker, chunk_start, chunk_end, prov, rows, fallback_used,
            )

        except Exception as exc:
            error_msg = str(exc)
            chunk_errors.append(f"{chunk_start}→{chunk_end}: {error_msg[:200]}")
            logger.error(
                "OHLCV ticker=%s chunk %s→%s failed: %s",
                ticker, chunk_start, chunk_end, error_msg,
            )
            # Continue to next chunk

    # ------------------------------------------------------------------
    # Determine ticker-level status
    # ------------------------------------------------------------------
    if chunks_succeeded > 0:
        status = "SUCCESS"
    else:
        status = "FAILED"

    min_written = str(global_min) if global_min is not None else ""
    max_written = str(global_max) if global_max is not None else ""
    error_str = "; ".join(chunk_errors[:3]) if chunk_errors else None

    # ------------------------------------------------------------------
    # Audit — one job_run_item per ticker
    # ------------------------------------------------------------------
    try:
        if status == "SUCCESS":
            details: dict = {
                "provider": last_provider,
                "rows": total_rows,
                "date_min": min_written,
                "date_max": max_written,
                "chunk_days": chunk_days,
                "chunks_attempted": chunks_attempted,
                "chunks_succeeded": chunks_succeeded,
                "first_chunk_start": str(chunks[0][0]),
                "last_chunk_end": str(chunks[-1][1]),
            }
            if chunk_errors:
                details["chunk_errors"] = chunk_errors
            job_run_item_repo.upsert(
                job_run_id=job_run_id,
                item_key=ticker,
                status="SUCCESS",
                error_details=json.dumps(details),
            )
        else:
            details = {
                "provider_attempted": "tradingview+yfinance",
                "chunk_days": chunk_days,
                "chunks_attempted": chunks_attempted,
                "chunks_succeeded": chunks_succeeded,
                "first_chunk_start": str(chunks[0][0]),
                "last_chunk_end": str(chunks[-1][1]),
                "errors": chunk_errors[:10],
            }
            job_run_item_repo.upsert(
                job_run_id=job_run_id,
                item_key=ticker,
                status="FAILED",
                error_summary="all chunks failed",
                error_details=json.dumps(details),
            )
    except Exception:
        pass

    return {
        "ticker": ticker,
        "status": status,
        "skipped": False,
        "provider_used": last_provider,
        "rows_written": total_rows,
        "requested_start": str(start_date),
        "requested_end": str(end_date),
        "min_written": min_written,
        "max_written": max_written,
        "chunks_attempted": chunks_attempted,
        "chunks_succeeded": chunks_succeeded,
        "error": error_str,
    }
