"""MCSA screen job — the orchestrator.

Fetches indicator values and fundamentals from upstream APIs, reads the
latest VCP result from the same schema, runs volume assessment and MCSA
scoring, and upserts results into ``mcsa_results``.

Architecture rules satisfied
-----------------------------
* §3.2 — Job orchestrates only; math lives in ``mcsa/`` modules.
* §3.3 — Continue on per-ticker failure; record in ``job_run_items``.
* §3.4 — Idempotent: upserts keyed by (ticker, as_of_date).
* §3.5 — Audit: ``job_runs`` created at start, finalised at end.
* Cross-context via HTTP only: fundamentals from Ingestor API,
  indicators from Indicator API.
* VCP results read from same schema (no cross-context violation).
"""

from __future__ import annotations

import logging
import traceback
from datetime import date, timedelta
from uuid import UUID

from ..clients.indicator_client import IndicatorClient
from ..clients.ingestor_client import IngestorClient
from ..db.engine import get_engine
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..repositories.job_run_repository import JobRunRepository
from ..mcsa.config import McsaConfig, build_mcsa_config
from ..mcsa.repositories.mcsa_result_repository import McsaResultRepository
from ..mcsa.repositories.vcp_result_read_repository import VcpResultReadRepository
from ..mcsa.scoring import (
    McsaInput,
    McsaResult,
    TrendInput,
    VcpInput,
    VolumeInput,
    FundamentalsInput,
    compute_mcsa_score,
)
from ..mcsa.volume_assessment import assess_volume

logger = logging.getLogger(__name__)


class McsaScreenJob:
    """Score an index using the MCSA algorithm.

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
        vcp_read_repo: VcpResultReadRepository | None = None,
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
        self.vcp_read_repo = vcp_read_repo or VcpResultReadRepository(_engine)

        self.mcsa_cfg: McsaConfig = build_mcsa_config(
            target_cfg.get("mcsa", {})
        )

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
            When set, score only this single ticker (CLI ``--ticker``).
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
            tickers = [{"symbol": ticker}]
        else:
            tickers = self.ingestor.get_index_members(index_code, country)
        if limit:
            tickers = tickers[:limit]

        succeeded = 0
        failed = 0
        errors: list[str] = []

        for member in tickers:
            tkr = member["symbol"]
            try:
                result_row = self._process_ticker(
                    tkr,
                    instrument_id=member.get("instrument_id"),
                    country=country,
                    job_run_id=job_run_id,
                )
                self.mcsa_result_repo.upsert([result_row])
                self.job_run_item_repo.create(
                    job_run_id=job_run_id,
                    item_key=tkr,
                    status="SUCCESS",
                )
                succeeded += 1
                logger.info(
                    "  %s  mcsa=%.1f  band=%s  trend=%.1f vcp=%.1f vol=%.1f fund=%.1f",
                    tkr,
                    result_row["mcsa_score"],
                    result_row["mcsa_band"],
                    result_row["trend_score"],
                    result_row["vcp_component"],
                    result_row["volume_score"],
                    result_row["fundamental_score"],
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
                logger.warning("  %s  FAILED  %s", tkr, msg)
                traceback.print_exc()

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
    # Per-ticker pipeline
    # ------------------------------------------------------------------

    def _process_ticker(
        self,
        ticker: str,
        *,
        instrument_id: str | None,
        country: str,
        job_run_id: UUID,
    ) -> dict:
        """Run the full MCSA pipeline for one ticker.

        Returns a dict ready for :meth:`McsaResultRepository.upsert`.
        """
        today = date.today()
        as_of_date = today.isoformat()

        # -- 1  Trend indicators -------------------------------------------
        trend_input = self._build_trend_input(ticker)

        # -- 2  VCP result (same schema) -----------------------------------
        vcp_input = self._build_vcp_input(ticker)

        # -- 3  Volume assessment ------------------------------------------
        volume_input = self._build_volume_input(ticker, today)

        # -- 4  Fundamentals -----------------------------------------------
        fundamentals_input = self._build_fundamentals_input(ticker, country)

        # -- 5  Scoring (pure math) ----------------------------------------
        mcsa_input = McsaInput(
            trend=trend_input,
            vcp=vcp_input,
            volume=volume_input,
            fundamentals=fundamentals_input,
        )
        result: McsaResult = compute_mcsa_score(mcsa_input, self.mcsa_cfg)

        # -- 6  Build result row -------------------------------------------
        return {
            "ticker": ticker,
            "instrument_id": instrument_id,
            "as_of_date": as_of_date,
            "mcsa_score": result.score,
            "mcsa_band": result.band,
            "trend_score": result.trend_score,
            "vcp_component": result.vcp_component,
            "volume_score": result.volume_score,
            "fundamental_score": result.fundamental_score,
            "evidence_json": result.evidence,
            "missing_fields": result.missing_fields,
            "created_by_job_run_id": str(job_run_id),
        }

    # ------------------------------------------------------------------
    # Input builders (each fetches from the right source)
    # ------------------------------------------------------------------

    def _build_trend_input(self, ticker: str) -> TrendInput:
        """Fetch latest indicator values for trend scoring."""
        sma_50 = self._get_indicator_value(ticker, "sma", 50)
        sma_150 = self._get_indicator_value(ticker, "sma", 150)
        sma_200 = self._get_indicator_value(ticker, "sma", 200)
        rolling_52w = self._get_indicator_value(ticker, "rolling_high", 252)

        # Latest price: use the most recent OHLCV close
        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        ohlcv = self.ingestor.get_ohlcv_range(ticker, from_date, today.isoformat())
        latest_price = float(ohlcv[-1]["close"]) if ohlcv else None

        return TrendInput(
            latest_price=latest_price,
            sma_50=sma_50,
            sma_150=sma_150,
            sma_200=sma_200,
            rolling_52w_high=rolling_52w,
        )

    def _build_vcp_input(self, ticker: str) -> VcpInput:
        """Read the latest VCP result from the same schema."""
        row = self.vcp_read_repo.get_latest_by_ticker(ticker)
        if row is None:
            return VcpInput()
        return VcpInput(
            vcp_score=float(row["vcp_score"]) if row.get("vcp_score") is not None else None,
            pattern_detected=bool(row.get("pattern_detected", False)),
        )

    def _build_volume_input(self, ticker: str, today: date) -> VolumeInput:
        """Fetch OHLCV + vol_sma and run volume assessment."""
        vol_cfg = self.mcsa_cfg.volume
        lookback_days = vol_cfg.lookback_days + vol_cfg.sma_window  # extra buffer
        from_date = (today - timedelta(days=lookback_days)).isoformat()
        to_date = today.isoformat()

        ohlcv_rows = self.ingestor.get_ohlcv_range(ticker, from_date, to_date)

        vol_sma = self._get_indicator_value(ticker, "vol_sma", vol_cfg.sma_window)

        assessment = assess_volume(ohlcv_rows, vol_sma, vol_cfg)
        if assessment is None:
            return VolumeInput()

        return VolumeInput(
            pullback_below_sma=assessment.pullback_below_sma,
            volume_dryup=assessment.volume_dryup,
            no_heavy_selling=assessment.no_heavy_selling,
        )

    def _build_fundamentals_input(
        self, ticker: str, country: str
    ) -> FundamentalsInput:
        """Fetch fundamentals from the Ingestor API."""
        data = self.ingestor.get_fundamentals_latest(
            symbol=ticker, country=country,
        )
        if data is None:
            return FundamentalsInput()

        return FundamentalsInput(
            revenue_growth_yoy=_safe_float(data.get("revenue_growth_yoy")),
            earnings_growth_yoy=_safe_float(data.get("earnings_growth_yoy")),
            roe=_safe_float(data.get("roe")),
            net_margin=_safe_float(data.get("net_margin")),
            debt_equity=_safe_float(data.get("debt_equity")),
        )

    # ------------------------------------------------------------------
    # Indicator helper
    # ------------------------------------------------------------------

    def _get_indicator_value(
        self, ticker: str, indicator: str, window: int
    ) -> float | None:
        """Fetch the latest single indicator value from the Indicator API."""
        resp = self.indicator.get_latest(ticker, indicator, window=window)
        if resp is None:
            return None
        val = resp.get("value")
        return float(val) if val is not None else None


# ======================================================================
# Module-level helpers
# ======================================================================


def _safe_float(val) -> float | None:
    """Convert *val* to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
