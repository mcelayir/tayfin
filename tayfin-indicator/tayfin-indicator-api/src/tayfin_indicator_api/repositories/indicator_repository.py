"""Indicator repository — read-only access to tayfin_indicator.indicator_series."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text


def ping_db(engine) -> bool:
    """Execute ``SELECT 1`` to verify database connectivity."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1


def get_latest(
    engine,
    ticker: str,
    indicator_key: str,
    params_json: dict | None = None,
) -> dict | None:
    """Return the most recent indicator row for *ticker* + *indicator_key*.

    Returns a dict with keys: ticker, as_of_date, indicator_key, params_json,
    value, source.  ``None`` if nothing found.
    """
    where = "WHERE ticker = :ticker AND indicator_key = :indicator_key"
    bind: dict = {"ticker": ticker, "indicator_key": indicator_key}

    if params_json is not None:
        where += " AND params_json = CAST(:params_json AS jsonb)"
        bind["params_json"] = json.dumps(params_json, sort_keys=True)

    sql = text(
        f"""
        SELECT ticker, as_of_date, indicator_key, params_json, value, source
        FROM tayfin_indicator.indicator_series
        {where}
        ORDER BY as_of_date DESC
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, bind).mappings().first()
        if row is None:
            return None
        return dict(row)


def get_range(
    engine,
    ticker: str,
    indicator_key: str,
    from_date: date,
    to_date: date,
    params_json: dict | None = None,
) -> list[dict]:
    """Return indicator rows for *ticker* between *from_date* and *to_date*."""
    where = (
        "WHERE ticker = :ticker AND indicator_key = :indicator_key "
        "AND as_of_date >= :from_date AND as_of_date <= :to_date"
    )
    bind: dict = {
        "ticker": ticker,
        "indicator_key": indicator_key,
        "from_date": from_date,
        "to_date": to_date,
    }

    if params_json is not None:
        where += " AND params_json = CAST(:params_json AS jsonb)"
        bind["params_json"] = json.dumps(params_json, sort_keys=True)

    sql = text(
        f"""
        SELECT as_of_date, value
        FROM tayfin_indicator.indicator_series
        {where}
        ORDER BY as_of_date ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, bind).mappings().all()
        return [dict(r) for r in rows]


def get_index_latest(
    engine,
    indicator_key: str,
    params_json: dict | None = None,
    tickers: list[str] | None = None,
) -> list[dict]:
    """Return the latest indicator row per ticker.

    If *tickers* is provided, only returns data for those tickers.
    Uses a window function to pick the most recent row per ticker.
    """
    params_filter = ""
    bind: dict = {"indicator_key": indicator_key}

    if params_json is not None:
        params_filter = "AND params_json = CAST(:params_json AS jsonb)"
        bind["params_json"] = json.dumps(params_json, sort_keys=True)

    ticker_filter = ""
    if tickers is not None and len(tickers) > 0:
        # Use ANY to filter by ticker list
        ticker_filter = "AND ticker = ANY(:tickers)"
        bind["tickers"] = tickers

    sql = text(
        f"""
        SELECT ticker, as_of_date, value
        FROM (
            SELECT ticker, as_of_date, value,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY as_of_date DESC) AS rn
            FROM tayfin_indicator.indicator_series
            WHERE indicator_key = :indicator_key
            {params_filter}
            {ticker_filter}
        ) sub
        WHERE rn = 1
        ORDER BY ticker
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, bind).mappings().all()
        return [dict(r) for r in rows]
