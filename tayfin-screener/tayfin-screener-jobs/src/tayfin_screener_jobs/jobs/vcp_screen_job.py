"""VCP screen job — the orchestrator.

Fetches OHLCV + indicator data from upstream APIs, runs the full
VCP pipeline (swing detection → contraction detection → feature
extraction → scoring), and upserts results into ``vcp_results``.

Architecture rules satisfied
-----------------------------
* §3.2 — Job orchestrates only; math lives in ``vcp/`` modules.
* §3.3 — Continue on per-ticker failure; record in ``job_run_items``.
* §3.4 — Idempotent: upserts keyed by (ticker, as_of_date).
* §3.5 — Audit: ``job_runs`` created at start, finalised at end.
"""

from __future__ import annotations

import logging
import traceback
from datetime import date, timedelta
from uuid import UUID

import pandas as pd

from ..clients.ingestor_client import IngestorClient
from ..clients.indicator_client import IndicatorClient
from ..db.engine import get_engine
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..repositories.job_run_repository import JobRunRepository
from ..vcp.contraction_detection import detect_contractions
from ..vcp.scoring import compute_vcp_score
from ..vcp.volatility_features import extract_volatility_features
from ..vcp.volume_features import extract_volume_features
from ..vcp.repositories.vcp_result_repository import VcpResultRepository

logger = logging.getLogger(__name__)


class VcpScreenJob:
    """Screen an index for VCP patterns.

    Lifecycle
    ---------
    1. ``from_config(...)`` — construct from YAML target config.
    2. ``run(...)``         — execute the pipeline.
    """

    JOB_NAME = "vcp_screen"

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
        vcp_result_repo: VcpResultRepository | None = None,
    ) -> None:
        self.target_name = target_name
        self.target_cfg = target_cfg
        self.full_cfg = full_cfg

        _engine = engine or get_engine()
        self.ingestor = ingestor_client or IngestorClient()
        self.indicator = indicator_client or IndicatorClient()
        self.job_run_repo = job_run_repo or JobRunRepository(_engine)
        self.job_run_item_repo = job_run_item_repo or JobRunItemRepository(_engine)
        self.vcp_result_repo = vcp_result_repo or VcpResultRepository(_engine)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        target_name: str,
        target_cfg: dict,
        full_cfg: dict,
    ) -> VcpScreenJob:
        """Build a :class:`VcpScreenJob` from YAML config dicts."""
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
        """Execute the VCP screen pipeline.

        Parameters
        ----------
        ticker
            When set, screen only this single ticker (CLI ``--ticker``).
        limit
            When set, cap the number of tickers processed (CLI ``--limit``).
        """
        index_code = self.target_cfg["index_code"]
        country = self.target_cfg.get("country", "US")
        lookback_days = self.target_cfg.get("lookback_days", 365)
        indicators_cfg = self.target_cfg.get("indicators", [])

        # --- audit: open job run ---
        job_run_id = self.job_run_repo.create(
            job_name=self.JOB_NAME,
            trigger_type="cli",
            config=self.target_cfg,
        )
        logger.info(
            "VcpScreenJob started  job_run=%s  target=%s  index=%s",
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
                    lookback_days=lookback_days,
                    indicators_cfg=indicators_cfg,
                    job_run_id=job_run_id,
                )
                self.vcp_result_repo.upsert([result_row])
                self.job_run_item_repo.create(
                    job_run_id=job_run_id,
                    item_key=tkr,
                    status="SUCCESS",
                )
                succeeded += 1
                logger.info(
                    "  %s  score=%.1f  confidence=%s  pattern=%s",
                    tkr,
                    result_row["vcp_score"],
                    result_row["vcp_confidence"],
                    result_row["pattern_detected"],
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
            "VcpScreenJob finished  job_run=%s  status=%s  total=%d  ok=%d  fail=%d",
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
        lookback_days: int,
        indicators_cfg: list[dict],
        job_run_id: UUID,
    ) -> dict:
        """Run the full VCP pipeline for one ticker.

        Returns a dict ready for :meth:`VcpResultRepository.upsert`.
        """
        today = date.today()
        from_date = (today - timedelta(days=lookback_days)).isoformat()
        to_date = today.isoformat()

        # -- 1  OHLCV data ------------------------------------------------
        ohlcv_rows = self.ingestor.get_ohlcv_range(ticker, from_date, to_date)
        if not ohlcv_rows:
            raise ValueError(f"No OHLCV data for {ticker}")

        df = _ohlcv_to_dataframe(ohlcv_rows)

        # -- 2  Indicator values -------------------------------------------
        ind = _build_indicator_map(indicators_cfg)
        latest, ranges = self._fetch_indicators(
            ticker, ind, from_date, to_date,
        )

        # -- 3  Contraction detection (pure math) --------------------------
        contraction_seq = detect_contractions(df["high"], df["low"])
        contraction_features = contraction_seq.to_dict()

        # -- 4  Volatility / trend features --------------------------------
        current_close = float(df["close"].iloc[-1])
        volatility_features = extract_volatility_features(
            current_close=current_close,
            sma_50=latest.get("sma_50", 0.0),
            sma_150=latest.get("sma_150", 0.0),
            sma_200=latest.get("sma_200", 0.0),
            rolling_high_252=latest.get("rolling_high_252", 0.0),
            atr_values=ranges.get("atr_20", []),
            sma_50_values=ranges.get("sma_50", []),
        )

        # -- 5  Volume features --------------------------------------------
        volume_values = df["volume"].tolist()
        volume_features = extract_volume_features(
            volume_values=volume_values,
            vol_sma_50_current=latest.get("vol_sma_50", 0.0),
            vol_sma_50_values=ranges.get("vol_sma_50", []),
        )

        # -- 6  Scoring ----------------------------------------------------
        scoring_result = compute_vcp_score(
            contraction_features=contraction_features,
            volatility_features=volatility_features,
            volume_features=volume_features,
        )

        # -- 7  Build result row -------------------------------------------
        features_json = {
            "contraction": contraction_features,
            "volatility": volatility_features,
            "volume": volume_features,
            "breakdown": scoring_result.breakdown,
        }

        return {
            "ticker": ticker,
            "instrument_id": instrument_id,
            "as_of_date": to_date,
            "vcp_score": scoring_result.score,
            "vcp_confidence": scoring_result.confidence,
            "pattern_detected": scoring_result.pattern_detected,
            "features_json": features_json,
            "created_by_job_run_id": str(job_run_id),
        }

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------

    def _fetch_indicators(
        self,
        ticker: str,
        ind: dict[str, tuple[str, int]],
        from_date: str,
        to_date: str,
    ) -> tuple[dict[str, float], dict[str, list[float]]]:
        """Fetch latest values and range series for all configured indicators.

        Parameters
        ----------
        ind
            ``{"sma_50": ("sma", 50), "atr_20": ("atr", 20), ...}``

        Returns
        -------
        latest
            ``{"sma_50": 185.3, "atr_20": 3.1, ...}``
        ranges
            ``{"sma_50": [180.1, 181.5, ...], "atr_20": [3.0, 3.1, ...]}``
        """
        latest: dict[str, float] = {}
        ranges: dict[str, list[float]] = {}

        for canon, (api_key, window) in ind.items():
            # latest single value
            resp = self.indicator.get_latest(ticker, api_key, window=window)
            if resp is not None:
                latest[canon] = float(resp.get("value", 0))

            # range time-series
            items = self.indicator.get_range(
                ticker, api_key, from_date, to_date, window=window,
            )
            ranges[canon] = [float(r["value"]) for r in items]

        return latest, ranges


# ======================================================================
# Module-level helpers (pure, no side effects)
# ======================================================================

def _ohlcv_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Convert ingestor OHLCV rows into a sorted DataFrame.

    Expected keys per row: ``as_of_date``, ``open``, ``high``, ``low``,
    ``close``, ``volume``.
    """
    df = pd.DataFrame(rows)
    df["as_of_date"] = pd.to_datetime(df["as_of_date"])
    df = df.sort_values("as_of_date").reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _build_indicator_map(indicators_cfg: list[dict]) -> dict[str, tuple[str, int]]:
    """Parse the ``indicators`` config list into a canonical-key → (api_key, window) map.

    Example input::

        [{"key": "sma", "window": 50}, {"key": "sma", "window": 150}]

    Returns::

        {"sma_50": ("sma", 50), "sma_150": ("sma", 150)}
    """
    result: dict[str, tuple[str, int]] = {}
    for entry in indicators_cfg:
        key = entry["key"]
        window = int(entry["window"])
        canon = f"{key}_{window}"
        result[canon] = (key, window)
    return result
