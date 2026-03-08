"""Read-only repository for tayfin_screener.mcsa_results.

All functions are pure reads — no writes.  The API is a read-only
façade over precomputed data (§6.1 ARCHITECTURE_RULES).
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Engine

SCHEMA = "tayfin_screener"
TABLE = f"{SCHEMA}.mcsa_results"


def get_latest_by_ticker(
    engine: Engine,
    ticker: str,
) -> dict | None:
    """Return the most recent MCSA result for *ticker*.

    Returns ``None`` when no data exists.
    """
    sql = text(f"""
        SELECT ticker, instrument_id, as_of_date,
               mcsa_pass, criteria_json, rs_rank,
               criteria_count_pass
        FROM {TABLE}
        WHERE ticker = :ticker
        ORDER BY as_of_date DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"ticker": ticker}).mappings().first()
        if row is None:
            return None
        return dict(row)


def get_latest_all(
    engine: Engine,
    *,
    pass_only: bool = False,
    min_criteria: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict]:
    """Return the latest MCSA result per ticker, ordered by rs_rank desc.

    Uses a window function to pick the most recent row per ticker.

    Parameters
    ----------
    pass_only
        When True, only include rows with ``mcsa_pass = true``.
    min_criteria
        When set, only include rows with ``criteria_count_pass >= min_criteria``.
    limit / offset
        Pagination.
    """
    filters: list[str] = []
    bind: dict = {"limit": limit, "offset": offset}

    if pass_only:
        filters.append("mcsa_pass = true")
    if min_criteria is not None:
        filters.append("criteria_count_pass >= :min_criteria")
        bind["min_criteria"] = min_criteria

    extra_where = ""
    if filters:
        extra_where = "AND " + " AND ".join(filters)

    sql = text(f"""
        WITH ranked AS (
            SELECT ticker, instrument_id, as_of_date,
                   mcsa_pass, criteria_json, rs_rank,
                   criteria_count_pass,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY as_of_date DESC) AS rn
            FROM {TABLE}
        )
        SELECT ticker, instrument_id, as_of_date,
               mcsa_pass, criteria_json, rs_rank,
               criteria_count_pass
        FROM ranked
        WHERE rn = 1
        {extra_where}
        ORDER BY rs_rank DESC
        LIMIT :limit OFFSET :offset
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, bind).mappings().all()
        return [dict(r) for r in rows]


def get_range_by_ticker(
    engine: Engine,
    ticker: str,
    from_date: date,
    to_date: date,
) -> list[dict]:
    """Return MCSA results for *ticker* between *from_date* and *to_date*."""
    sql = text(f"""
        SELECT ticker, instrument_id, as_of_date,
               mcsa_pass, criteria_json, rs_rank,
               criteria_count_pass
        FROM {TABLE}
        WHERE ticker = :ticker
          AND as_of_date >= :from_date
          AND as_of_date <= :to_date
        ORDER BY as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"ticker": ticker, "from_date": from_date, "to_date": to_date},
        ).mappings().all()
        return [dict(r) for r in rows]
