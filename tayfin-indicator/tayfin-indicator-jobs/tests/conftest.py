"""Shared fixtures for tayfin-indicator-jobs tests."""

from __future__ import annotations

from datetime import date, timedelta


def make_ohlcv_candles(
    n: int = 10,
    start_date: date | None = None,
    base_close: float = 100.0,
    step: float = 1.0,
) -> list[dict]:
    """Return *n* deterministic OHLCV candle dicts.

    close values: base_close, base_close+step, …
    high = close + 2, low = close - 2, volume = 1_000_000 * i
    """
    if start_date is None:
        start_date = date(2025, 1, 2)

    candles: list[dict] = []
    d = start_date
    for i in range(n):
        c = base_close + step * i
        candles.append(
            {
                "as_of_date": d.isoformat(),
                "open": c - 0.5,
                "high": c + 2.0,
                "low": c - 2.0,
                "close": c,
                "volume": 1_000_000 * (i + 1),
            }
        )
        d += timedelta(days=1)
        # Skip weekends (simplistic)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    return candles
