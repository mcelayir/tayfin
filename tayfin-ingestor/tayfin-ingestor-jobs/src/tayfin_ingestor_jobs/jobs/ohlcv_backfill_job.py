"""OHLCV backfill job — historical range ingestion via the shared service."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from ..db.engine import get_engine
from ..ohlcv.service import run_ohlcv_ingestion

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Output directory lives alongside config/ and scripts/ inside ingestor-jobs
_JOBS_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # → tayfin-ingestor-jobs/
_OUT_DIR = _JOBS_ROOT / "out" / "backfill"


class OhlcvBackfillJob:
    """Backfill OHLCV daily candles for a large historical window.

    Thin wrapper that validates CLI date-mode semantics and delegates
    all real work to :func:`run_ohlcv_ingestion`.
    """

    def __init__(
        self,
        engine=None,
        target_cfg: dict | None = None,
        global_cfg: dict | None = None,
    ):
        self.engine = engine or get_engine()
        self.target_cfg = target_cfg or {}
        self.global_cfg = global_cfg or {}

    @classmethod
    def from_config(
        cls, target_cfg: dict, global_cfg: dict | None = None,
    ) -> "OhlcvBackfillJob":
        return cls(target_cfg=target_cfg, global_cfg=global_cfg)

    # ------------------------------------------------------------------
    # Date resolution — mutually exclusive modes
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_date_range(
        *,
        days_back: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> tuple[date, date]:
        """Resolve start/end dates from exactly one of the two modes.

        Mode 1 — ``--days-back N``:
            start = today - N, end = today

        Mode 2 — ``--from … --to …``:
            both required, YYYY-MM-DD, from <= to

        Raises
        ------
        ValueError
            If no mode, both modes, or invalid dates are given.
        """
        has_days_back = days_back is not None
        has_range = from_date is not None or to_date is not None

        if has_days_back and has_range:
            raise ValueError(
                "Cannot mix --days-back with --from/--to.  "
                "Provide exactly one date mode."
            )

        if not has_days_back and not has_range:
            raise ValueError(
                "A date mode is required.  "
                "Use --days-back N  or  --from YYYY-MM-DD --to YYYY-MM-DD."
            )

        # Mode 1: days-back
        if has_days_back:
            if days_back <= 0:
                raise ValueError("--days-back must be a positive integer.")
            end = date.today()
            start = end - timedelta(days=days_back)
            return start, end

        # Mode 2: explicit range
        if from_date is None or to_date is None:
            raise ValueError(
                "--from and --to must both be provided for range mode."
            )

        if not _DATE_RE.match(from_date):
            raise ValueError(
                f"Invalid --from date '{from_date}'. Expected YYYY-MM-DD."
            )
        if not _DATE_RE.match(to_date):
            raise ValueError(
                f"Invalid --to date '{to_date}'. Expected YYYY-MM-DD."
            )

        try:
            start = date.fromisoformat(from_date)
        except ValueError:
            raise ValueError(
                f"Invalid --from date '{from_date}'. Expected YYYY-MM-DD."
            )

        try:
            end = date.fromisoformat(to_date)
        except ValueError:
            raise ValueError(
                f"Invalid --to date '{to_date}'. Expected YYYY-MM-DD."
            )

        if start > end:
            raise ValueError(
                f"--from ({start}) must not be after --to ({end})."
            )

        return start, end

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        days_back: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        chunk_days: Optional[int] = None,
        skip_existing: bool = False,
    ) -> None:
        start, end = self.resolve_date_range(
            days_back=days_back,
            from_date=from_date,
            to_date=to_date,
        )

        # Resolve chunk_days: CLI flag > config > None
        effective_chunk_days = (
            chunk_days
            if chunk_days is not None
            else self.target_cfg.get("default_chunk_days")
        )

        target_name = self.target_cfg.get("index_code", "unknown")

        logger.info(
            "OHLCV backfill — target=%s window=%s→%s ticker=%s "
            "chunk_days=%s skip_existing=%s",
            target_name,
            start, end, ticker,
            effective_chunk_days, skip_existing,
        )

        summary = run_ohlcv_ingestion(
            target_name=target_name,
            cfg=self.target_cfg,
            start_date=start,
            end_date=end,
            ticker=ticker,
            limit=limit,
            chunk_days=effective_chunk_days,
            skip_existing=skip_existing,
            engine=self.engine,
        )

        # Build request metadata for the report
        request_meta = {
            "start": str(start),
            "end": str(end),
            "days_back": days_back,
            "chunk_days": effective_chunk_days,
            "skip_existing": skip_existing,
        }

        self._print_summary(summary)
        self._write_report(summary, target_name, request_meta)

    # ------------------------------------------------------------------
    # CLI summary
    # ------------------------------------------------------------------

    _SUMMARY_COLUMNS = [
        "ticker",
        "status",
        "skipped",
        "provider_used",
        "rows_written",
        "requested_start",
        "requested_end",
        "min_written",
        "max_written",
        "chunks_attempted",
        "chunks_succeeded",
        "error",
    ]

    @classmethod
    def _print_summary(cls, summary: dict) -> None:
        items = summary["items"]
        if items:
            df = pd.DataFrame(items)
            # Ensure all expected columns exist; fill missing with ""
            for col in cls._SUMMARY_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df = df[cls._SUMMARY_COLUMNS]
            print(df.to_markdown(index=False), flush=True)
        print(
            f"\nTotal: {summary['total']}  Succeeded: {summary['succeeded']}  "
            f"Failed: {summary['failed']}",
            flush=True,
        )

    # ------------------------------------------------------------------
    # JSON report
    # ------------------------------------------------------------------

    @staticmethod
    def _write_report(
        summary: dict,
        target_name: str,
        request_meta: dict,
    ) -> None:
        items = summary["items"]

        tickers_skipped = sum(1 for i in items if i.get("skipped"))
        rows_written_total = sum(i.get("rows_written", 0) for i in items)

        report = {
            "job": "ohlcv_backfill",
            "target": target_name,
            "requested": request_meta,
            "stats": {
                "tickers_total": summary["total"],
                "tickers_succeeded": summary["succeeded"],
                "tickers_failed": summary["failed"],
                "tickers_skipped": tickers_skipped,
                "rows_written_total": rows_written_total,
            },
            "items": items,
        }

        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ohlcv_backfill_{target_name}_{ts}.json"
        path = _OUT_DIR / filename

        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("Backfill report written → %s", path)
        print(f"\nReport: {path}", flush=True)
