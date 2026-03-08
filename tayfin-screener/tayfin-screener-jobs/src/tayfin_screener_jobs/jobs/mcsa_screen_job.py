"""MCSA screen job — the orchestrator.

Fetches indicator data from the Indicator API (cross-context via HTTP)
and OHLCV from the Ingestor API, computes RS ranking across the screened
universe, evaluates the 8 Minervini criteria per ticker, and upserts
results into ``mcsa_results``.

Architecture rules satisfied
-----------------------------
* §2.1 — Cross-context data via HTTP APIs only.
* §3.2 — Job orchestrates only; math lives in ``mcsa/`` modules.
* §3.3 — Continue on per-ticker failure; record in ``job_run_items``.
* §3.4 — Idempotent: upserts keyed by (ticker, as_of_date).
* §3.5 — Audit: ``job_runs`` created at start, finalised at end.

ADR-0001 compliance
--------------------
* D1 — RS ranking computed screener-side (not stored as indicator).
* D4 — RS formula: (stock_6mo_return / ndx_6mo_return) * 100.
* ARCH_BLOCKER — Uses 6 bulk get_index_latest() calls, not 600 individual.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from uuid import UUID

import pandas as pd

from ..clients.indicator_client import IndicatorClient
from ..clients.ingestor_client import IngestorClient
from ..db.engine import get_engine
from ..mcsa.evaluate import McsaResult, evaluate_mcsa
from ..mcsa.repositories.mcsa_result_repository import McsaResultRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..repositories.job_run_repository import JobRunRepository

logger = logging.getLogger(__name__)

# RS ranking lookback: ~126 trading days ≈ 6 calendar months
_RS_LOOKBACK_CALENDAR_DAYS = 185


class McsaScreenJob:
    """Screen an index for Minervini Trend Template compliance.

    Lifecycle
    ---------
    1. ``from_config(...)`` — construct from YAML target config.
    2. ``run(...)``         — execute the pipeline.
    """

    JOB_NAME = "mcsa_screen"

    def __init__(
        self,
        target_name: str,
        target_cfg: dict,
        full_cfg: dict,
        *,
        engine=None,
        ingestor_client: IngestorClient | None = None,
        indicator_client: IndicatorClient | None = None,
        job_run_repo: JobRunRepository | None = None,
        job_run_item_repo: JobRunItemRepository | None = None,
        mcsa_result_repo: McsaResultRepository | None = None,
    ) -> None:
        self.target_name = target_name
        self.target_cfg = target_cfg
        self.full_cfg = full_cfg

        _engine = engine or get_engine()
        self.ingestor = ingestor_client or IngestorClient()
        self.indicator = indicator_client or IndicatorClient()
        self.job_run_repo = job_run_repo or JobRunRepository(_engine)
        self.job_run_item_repo = job_run_item_repo or JobRunItemRepository(_engine)
        self.mcsa_result_repo = mcsa_result_repo or McsaResultRepository(_engine)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        target_name: str,
        target_cfg: dict,
        full_cfg: dict,
    ) -> McsaScreenJob:
        """Build a :class:`McsaScreenJob` from YAML config dicts."""
        return cls(
            target_name=target_name,
            target_cfg=target_cfg,
            full_cfg=full_cfg,
        )

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        ticker: str | None = None,
        limit: int | None = None,
    ) -> None:
        """Execute the MCSA screen pipeline.

        Parameters
        ----------
        ticker
            When set, screen only this single ticker (CLI ``--ticker``).
        limit
            When set, cap the number of tickers processed (CLI ``--limit``).
        """
        index_code = self.target_cfg["index_code"]
        country = self.target_cfg.get("country", "US")

        # --- audit: open job run ---
        job_run_id = self.job_run_repo.create(
            job_name=self.JOB_NAME,
            trigger_type="cli",
            config=self.target_cfg,
        )
        logger.info(
            "McsaScreenJob started  job_run=%s  target=%s  index=%s",
            job_run_id, self.target_name, index_code,
        )

        # --- resolve tickers ---
        if ticker:
            members = [{"symbol": ticker.upper()}]
        else:
            members = self.ingestor.get_index_members(index_code, country)
        if limit:
            members = members[:limit]

        tickers = [m["symbol"] for m in members]
        instrument_map = {
            m["symbol"]: m.get("instrument_id") for m in members
        }

        logger.info("Resolved %d tickers for %s", len(tickers), index_code)

        # --- Step 1: Bulk-fetch indicators (6 calls, not 600) ---
        indicator_data = self._fetch_bulk_indicators(index_code)

        # --- Step 2: Fetch OHLCV for RS calculation ---
        rs_ranking = self._compute_rs_ranking(tickers, index_code)

        # --- Step 3: Fetch recent close + SMA-50 for criterion 8 ---
        recent_data = self._fetch_recent_data(tickers)

        # --- Step 4: Evaluate each ticker ---
        succeeded = 0
        failed = 0
        errors: list[str] = []

        for tkr in tickers:
            try:
                mcsa_result = self._evaluate_ticker(
                    tkr,
                    indicator_data=indicator_data,
                    rs_ranking=rs_ranking,
                    recent_data=recent_data,
                )

                result_row = {
                    "ticker": tkr,
                    "instrument_id": instrument_map.get(tkr),
                    "as_of_date": mcsa_result.as_of_date.isoformat(),
                    "mcsa_pass": mcsa_result.mcsa_pass,
                    "criteria_json": mcsa_result.criteria_json,
                    "rs_rank": mcsa_result.rs_rank,
                    "criteria_count_pass": mcsa_result.criteria_count_pass,
                    "created_by_job_run_id": str(job_run_id),
                    "updated_by_job_run_id": str(job_run_id),
                }
                self.mcsa_result_repo.upsert([result_row])
                self.job_run_item_repo.create(
                    job_run_id=job_run_id,
                    item_key=tkr,
                    status="SUCCESS",
                )
                succeeded += 1
                logger.info(
                    "  %s  pass=%s  criteria=%d/8  rs_rank=%.1f",
                    tkr,
                    mcsa_result.mcsa_pass,
                    mcsa_result.criteria_count_pass,
                    mcsa_result.rs_rank,
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                msg = f"{type(exc).__name__}: {exc}"
                errors.append(f"{tkr}: {msg}")
                self.job_run_item_repo.create(
                    job_run_id=job_run_id,
                    item_key=tkr,
                    status="FAILED",
                    error_summary=msg,
                )
                logger.warning("  %s  FAILED  %s", tkr, msg, exc_info=True)

        # --- audit: finalise job run ---
        total = succeeded + failed
        status = "SUCCESS" if failed == 0 else "FAILED"
        error_summary = "; ".join(errors[:10]) if errors else None
        self.job_run_repo.finalize(
            job_run_id=job_run_id,
            status=status,
            items_total=total,
            items_succeeded=succeeded,
            items_failed=failed,
            error_summary=error_summary,
        )
        logger.info(
            "McsaScreenJob finished  job_run=%s  status=%s  total=%d  ok=%d  fail=%d",
            job_run_id, status, total, succeeded, failed,
        )

    # ------------------------------------------------------------------
    # Bulk indicator fetching (ADR-0001 ARCH_BLOCKER resolution)
    # ------------------------------------------------------------------

    def _fetch_bulk_indicators(
        self,
        index_code: str,
    ) -> dict[str, dict[str, float]]:
        """Fetch 6 indicator series in bulk — one call each.

        Returns a nested dict: ``{indicator_canon: {ticker: value}}``.
        Example: ``{"sma_50": {"AAPL": 185.3, "MSFT": 420.1, ...}}``.
        """
        # (canonical_key, api_indicator_key, window)
        indicators_needed = [
            ("sma_50", "sma", 50),
            ("sma_150", "sma", 150),
            ("sma_200", "sma", 200),
            ("rolling_high_252", "rolling_high", 252),
            ("rolling_low_252", "rolling_low", 252),
            ("sma_slope_200", "sma_slope", 200),
        ]

        data: dict[str, dict[str, float]] = {}

        for canon, api_key, window in indicators_needed:
            items = self.indicator.get_index_latest(index_code, api_key, window)
            data[canon] = {
                item["ticker"]: float(item["value"])
                for item in items
                if item.get("value") is not None
            }
            logger.info(
                "  Fetched %s: %d tickers", canon, len(data[canon]),
            )

        return data

    # ------------------------------------------------------------------
    # RS ranking (ADR-0001 §D1 + §D4)
    # ------------------------------------------------------------------

    def _compute_rs_ranking(
        self,
        tickers: list[str],
        index_code: str,
    ) -> dict[str, float]:
        """Compute RS ranking for all tickers relative to NDX benchmark.

        RS_raw = (stock_6mo_return / benchmark_6mo_return) * 100
        RS_rank = percentile across all tickers in the universe.

        Returns ``{ticker: percentile_rank}`` where rank is 0–100.
        """
        today = date.today()
        from_date = (today - timedelta(days=_RS_LOOKBACK_CALENDAR_DAYS)).isoformat()
        to_date = today.isoformat()

        # Fetch benchmark (NDX index) OHLCV
        ndx_ohlcv = self.ingestor.get_ohlcv_range(index_code, from_date, to_date)
        if not ndx_ohlcv:
            logger.warning("No NDX OHLCV data for RS calculation — all ranks = 50")
            return {t: 50.0 for t in tickers}

        benchmark_return = _compute_return(ndx_ohlcv)

        # Fetch per-ticker 6-month returns
        stock_returns: dict[str, float] = {}
        for tkr in tickers:
            try:
                ohlcv = self.ingestor.get_ohlcv_range(tkr, from_date, to_date)
                if ohlcv:
                    stock_returns[tkr] = _compute_return(ohlcv)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to fetch OHLCV for %s RS calc", tkr)

        if not stock_returns:
            return {t: 50.0 for t in tickers}

        # Compute RS raw
        rs_raw: dict[str, float] = {}
        for tkr, ret in stock_returns.items():
            if benchmark_return != 0:
                rs_raw[tkr] = (ret / benchmark_return) * 100
            else:
                rs_raw[tkr] = 0.0

        # Compute percentile rankings
        sorted_values = sorted(rs_raw.values())
        n = len(sorted_values)
        if n == 0:
            return {t: 50.0 for t in tickers}

        rs_ranking: dict[str, float] = {}
        for tkr, raw in rs_raw.items():
            # Count values below this one for percentile
            rank_below = sum(1 for v in sorted_values if v < raw)
            rs_ranking[tkr] = (rank_below / n) * 100

        # Fill missing tickers with median
        for tkr in tickers:
            if tkr not in rs_ranking:
                rs_ranking[tkr] = 50.0

        return rs_ranking

    # ------------------------------------------------------------------
    # Recent data for Criterion 8
    # ------------------------------------------------------------------

    def _fetch_recent_data(
        self,
        tickers: list[str],
    ) -> dict[str, dict]:
        """Fetch last 10 days of close prices and SMA-50 for criterion 8.

        Returns ``{ticker: {"closes": [...], "sma_50": [...]}}``.
        """
        today = date.today()
        from_date = (today - timedelta(days=20)).isoformat()  # ~10 trading days
        to_date = today.isoformat()

        result: dict[str, dict] = {}

        for tkr in tickers:
            try:
                ohlcv = self.ingestor.get_ohlcv_range(tkr, from_date, to_date)
                sma_items = self.indicator.get_range(
                    tkr, "sma", from_date, to_date, window=50,
                )

                closes = [float(r["close"]) for r in ohlcv][-10:] if ohlcv else []
                sma_50_vals = [float(r["value"]) for r in sma_items][-10:] if sma_items else []

                # Reverse so newest first (as criterion_8 expects)
                result[tkr] = {
                    "closes": list(reversed(closes)),
                    "sma_50": list(reversed(sma_50_vals)),
                }
            except Exception:  # noqa: BLE001
                logger.warning("Failed to fetch recent data for %s", tkr)
                result[tkr] = {"closes": [], "sma_50": []}

        return result

    # ------------------------------------------------------------------
    # Per-ticker evaluation
    # ------------------------------------------------------------------

    def _evaluate_ticker(
        self,
        ticker: str,
        *,
        indicator_data: dict[str, dict[str, float]],
        rs_ranking: dict[str, float],
        recent_data: dict[str, dict],
    ) -> McsaResult:
        """Evaluate the 8 MCSA criteria for one ticker.

        Delegates to the pure ``evaluate_mcsa()`` function.
        """
        # Extract indicator values for this ticker
        sma_50 = indicator_data.get("sma_50", {}).get(ticker)
        sma_150 = indicator_data.get("sma_150", {}).get(ticker)
        sma_200 = indicator_data.get("sma_200", {}).get(ticker)
        rolling_high_252 = indicator_data.get("rolling_high_252", {}).get(ticker)
        rolling_low_252 = indicator_data.get("rolling_low_252", {}).get(ticker)
        sma_slope_200 = indicator_data.get("sma_slope_200", {}).get(ticker)

        # Validate all required indicators exist
        missing = []
        if sma_50 is None:
            missing.append("sma_50")
        if sma_150 is None:
            missing.append("sma_150")
        if sma_200 is None:
            missing.append("sma_200")
        if rolling_high_252 is None:
            missing.append("rolling_high_252")
        if rolling_low_252 is None:
            missing.append("rolling_low_252")
        if sma_slope_200 is None:
            missing.append("sma_slope_200")

        if missing:
            raise ValueError(
                f"Missing indicator data for {ticker}: {missing}"
            )

        # Get close from recent data (newest = first element)
        recent = recent_data.get(ticker, {"closes": [], "sma_50": []})
        if not recent["closes"]:
            raise ValueError(f"No recent close data for {ticker}")

        close = recent["closes"][0]  # newest first
        rs_rank = rs_ranking.get(ticker, 50.0)

        # Align recent lists for criterion 8
        recent_closes = recent["closes"][:10]
        recent_sma_50 = recent["sma_50"][:10]

        # Pad if insufficient data (fail-safe: criterion 8 will likely fail)
        min_len = min(len(recent_closes), len(recent_sma_50))
        recent_closes = recent_closes[:min_len]
        recent_sma_50 = recent_sma_50[:min_len]

        if min_len == 0:
            raise ValueError(f"No recent data available for {ticker} criterion 8")

        return evaluate_mcsa(
            ticker=ticker,
            as_of_date=date.today(),
            close=close,
            sma_50=sma_50,
            sma_150=sma_150,
            sma_200=sma_200,
            sma_200_slope=sma_slope_200,
            rolling_high_252=rolling_high_252,
            rolling_low_252=rolling_low_252,
            rs_rank=rs_rank,
            recent_closes=recent_closes,
            recent_sma_50=recent_sma_50,
        )


# ======================================================================
# Module-level helpers (pure, no side effects)
# ======================================================================

def _compute_return(ohlcv_rows: list[dict]) -> float:
    """Compute percentage return from OHLCV rows.

    Return = (latest_close - earliest_close) / earliest_close
    """
    if not ohlcv_rows or len(ohlcv_rows) < 2:
        return 0.0

    # Sort by date
    sorted_rows = sorted(ohlcv_rows, key=lambda r: r.get("as_of_date", ""))
    earliest_close = float(sorted_rows[0]["close"])
    latest_close = float(sorted_rows[-1]["close"])

    if earliest_close == 0:
        return 0.0

    return (latest_close - earliest_close) / earliest_close
