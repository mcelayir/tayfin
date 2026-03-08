"""Read-only repository for tayfin_screener.mcsa_results.

All functions are pure reads — no writes.  The API is a read-only
façade over precomputed data (§6.1 ARCHITECTURE_RULES).
"""

from __future__ import annotations

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
               mcsa_score, mcsa_band,
               trend_score, vcp_component, volume_score, fundamental_score,
               evidence_json, missing_fields
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
    band: str | None = None,
    min_score: float | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict]:
    """Return the latest MCSA result per ticker, ordered by score desc.

    Parameters
    ----------
    band
        When set, only include rows with the specified band
        (``strong``, ``watchlist``, ``neutral``, ``weak``).
    min_score
        When set, only include rows with ``mcsa_score >= min_score``.
    limit / offset
        Pagination.
    """
    filters: list[str] = []
    bind: dict = {"limit": limit, "offset": offset}

    if band is not None:
        filters.append("mcsa_band = :band")
        bind["band"] = band
    if min_score is not None:
        filters.append("mcsa_score >= :min_score")
        bind["min_score"] = min_score

    extra_where = ""
    if filters:
        extra_where = "AND " + " AND ".join(filters)

    sql = text(f"""
        WITH ranked AS (
            SELECT ticker, instrument_id, as_of_date,
                   mcsa_score, mcsa_band,
                   trend_score, vcp_component, volume_score, fundamental_score,
                   evidence_json, missing_fields,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY as_of_date DESC) AS rn
            FROM {TABLE}
        )
        SELECT ticker, instrument_id, as_of_date,
               mcsa_score, mcsa_band,
               trend_score, vcp_component, volume_score, fundamental_score,
               evidence_json, missing_fields
        FROM ranked
        WHERE rn = 1
        {extra_where}
        ORDER BY mcsa_score DESC
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
               mcsa_score, mcsa_band,
               trend_score, vcp_component, volume_score, fundamental_score,
               evidence_json, missing_fields
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
