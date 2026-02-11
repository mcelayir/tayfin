"""OHLCV response serializers.

Centralises type coercion and key naming so every OHLCV endpoint
returns a predictable, JSON-safe shape.
"""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Any


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _to_float(v: Any) -> float:
    """Coerce a numeric value to float.  Raises ValueError on NaN/None."""
    if v is None:
        raise ValueError("unexpected None in numeric OHLCV field")
    if isinstance(v, Decimal):
        f = float(v)
    elif isinstance(v, (int, float)):
        f = float(v)
    else:
        raise ValueError(f"unexpected type {type(v).__name__} in numeric OHLCV field")
    if math.isnan(f) or math.isinf(f):
        raise ValueError(f"unexpected {f} in numeric OHLCV field")
    return f


def _to_int(v: Any) -> int:
    """Coerce volume to int.  Accepts int, float, or Decimal."""
    if v is None:
        raise ValueError("unexpected None for volume")
    if isinstance(v, Decimal):
        return int(v)
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"unexpected {v} for volume")
        return int(v)
    return int(v)


def _date_str(d: Any) -> str:
    """as_of_date → 'YYYY-MM-DD' string."""
    if isinstance(d, date):
        return d.isoformat()
    return str(d)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def serialize_candle(row: dict) -> dict:
    """Serialize a single OHLCV candle dict to a JSON-safe shape.

    Expected input keys: ticker, as_of_date, open, high, low, close,
    volume, source.
    """
    return {
        "ticker": row["ticker"],
        "as_of_date": _date_str(row["as_of_date"]),
        "open": _to_float(row["open"]),
        "high": _to_float(row["high"]),
        "low": _to_float(row["low"]),
        "close": _to_float(row["close"]),
        "volume": _to_int(row["volume"]),
        "source": row["source"],
    }


def serialize_series(
    ticker: str,
    from_date: date | None,
    to_date: date | None,
    items: list[dict],
) -> dict:
    """Wrap a list of candles into a range-query response envelope."""
    return {
        "ticker": ticker,
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
        "count": len(items),
        "items": [serialize_candle(it) for it in items],
    }


def serialize_index_latest(index_code: str, items: list[dict]) -> dict:
    """Wrap per-ticker latest candles into an index-latest response envelope."""
    serialized = [serialize_candle(it) for it in items]
    serialized.sort(key=lambda c: c["ticker"])
    return {
        "index_code": index_code,
        "count": len(serialized),
        "items": serialized,
    }
