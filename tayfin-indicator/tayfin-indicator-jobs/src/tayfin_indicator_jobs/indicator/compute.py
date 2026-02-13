"""Pure computation functions for technical indicators.

Each function accepts a pandas Series (or DataFrame columns) and returns
a pandas Series of indicator values.  No DB, no network — pure math.
"""

from __future__ import annotations

import pandas as pd


def compute_sma(close: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average of *close* over *window* periods.

    Returns a Series of the same length; the first ``window - 1`` values
    will be NaN.
    """
    return close.rolling(window=window).mean()


def compute_true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> pd.Series:
    """True Range series.

    TR_t = max(high_t − low_t,
               |high_t − close_{t-1}|,
               |low_t  − close_{t-1}|)

    For the very first row (no previous close) TR = high − low.
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # First row: no previous close → use high − low
    tr.iloc[0] = float(high.iloc[0]) - float(low.iloc[0])
    return tr


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int,
) -> pd.Series:
    """Average True Range = SMA(TR, *window*)."""
    tr = compute_true_range(high, low, close)
    return tr.rolling(window=window).mean()


def compute_vol_sma(volume: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average of *volume* over *window* periods."""
    return volume.rolling(window=window).mean()


def compute_rolling_high(close: pd.Series, window: int) -> pd.Series:
    """Rolling maximum of *close* over *window* periods."""
    return close.astype(float).rolling(window=window).max()
