"""Read-only repository for tayfin_screener.vcp_results (same schema).

Used by MCSA jobs to read the latest VCP screening result for a ticker
without crossing bounded-context boundaries (VCP and MCSA share the
tayfin_screener schema).
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"
TABLE = f"{SCHEMA}.vcp_results"


class VcpResultReadRepository:
    """Read-only access to vcp_results for MCSA consumption."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_latest_by_ticker(self, ticker: str) -> dict | None:
        """Return the most recent VCP result row for *ticker*, or None."""
        stmt = text(f"""
            SELECT ticker,
                   as_of_date,
                   vcp_score,
                   vcp_confidence,
                   pattern_detected,
                   features_json
              FROM {TABLE}
             WHERE ticker = :ticker
             ORDER BY as_of_date DESC
             LIMIT 1
        """)

        with self._engine.connect() as conn:
            row = conn.execute(stmt, {"ticker": ticker}).mappings().first()
            if row is None:
                logger.debug("No VCP result found for %s", ticker)
                return None

            return dict(row)

    def get_latest_all(self) -> list[dict]:
        """Return the latest VCP result per ticker (all tickers).

        Uses a DISTINCT ON query to get one row per ticker, ordered by
        most recent as_of_date.
        """
        stmt = text(f"""
            SELECT DISTINCT ON (ticker)
                   ticker,
                   as_of_date,
                   vcp_score,
                   vcp_confidence,
                   pattern_detected,
                   features_json
              FROM {TABLE}
             ORDER BY ticker, as_of_date DESC
        """)

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [dict(r) for r in rows]
