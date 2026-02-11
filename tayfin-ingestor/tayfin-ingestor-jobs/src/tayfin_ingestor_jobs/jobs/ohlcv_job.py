"""OHLCV job — thin wrapper around the shared ingestion service."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from ..db.engine import get_engine
from ..ohlcv.service import run_ohlcv_ingestion

logger = logging.getLogger(__name__)


class OhlcvJob:
    """Daily OHLCV ingestion job.

    Thin wrapper that resolves configuration and the date window,
    delegates all real work to :func:`run_ohlcv_ingestion`, and
    prints a CLI-friendly summary table.
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
    def from_config(cls, target_cfg: dict, global_cfg: dict | None = None) -> "OhlcvJob":
        return cls(target_cfg=target_cfg, global_cfg=global_cfg)

    # ------------------------------------------------------------------
    # Date resolution (stays in the wrapper — CLI concern)
    # ------------------------------------------------------------------

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
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        ticker: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit_tickers: Optional[int] = None,
    ) -> None:
        start, end = self.resolve_date_window(from_date, to_date)

        summary = run_ohlcv_ingestion(
            target_name=self.target_cfg.get("index_code", "unknown"),
            cfg=self.target_cfg,
            start_date=start,
            end_date=end,
            ticker=ticker,
            limit=limit_tickers,
            engine=self.engine,
        )

        self._print_summary(summary)

    # ------------------------------------------------------------------
    # CLI summary
    # ------------------------------------------------------------------

    @staticmethod
    def _print_summary(summary: dict) -> None:
        items = summary["items"]
        if items:
            df = pd.DataFrame(items)
            print(df.to_markdown(index=False), flush=True)
        print(
            f"\nTotal: {summary['total']}  Succeeded: {summary['succeeded']}  "
            f"Failed: {summary['failed']}",
            flush=True,
        )
