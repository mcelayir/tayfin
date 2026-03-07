"""Swing-point detection for VCP analysis.

Pure computation functions that operate on pandas Series.  No DB, no network —
pure math.

A **swing high** is a local maximum where the high price is greater than
the highs of the surrounding *order* bars on both sides.

A **swing low** is a local minimum where the low price is less than
the lows of the surrounding *order* bars on both sides.

These swing points form the skeleton from which VCP contractions
(progressively tighter highs and higher lows) are measured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SwingPoint:
    """A single detected swing high or swing low."""

    index: int
    """Bar index (positional, 0-based) within the source DataFrame."""
    date: str
    """ISO date string (YYYY-MM-DD) of the bar."""
    price: float
    """The high (for swing highs) or low (for swing lows) price at this bar."""
    kind: Literal["high", "low"]
    """Whether the point is a swing high or swing low."""


# ------------------------------------------------------------------
# Core detection
# ------------------------------------------------------------------

def detect_swing_highs(
    high: pd.Series,
    order: int = 5,
) -> list[SwingPoint]:
    """Return swing-high points where *high[i]* exceeds its *order* neighbours.

    Parameters
    ----------
    high : pd.Series
        Series of high prices, indexed by date (or any label).
    order : int
        Number of bars on each side a high must dominate.
        Must be >= 1.

    Returns
    -------
    list[SwingPoint]
        Detected swing highs in chronological order.
    """
    if order < 1:
        raise ValueError(f"order must be >= 1, got {order}")
    points: list[SwingPoint] = []
    values = high.values
    n = len(values)
    for i in range(order, n - order):
        val = values[i]
        is_swing = True
        for j in range(1, order + 1):
            if values[i - j] >= val or values[i + j] >= val:
                is_swing = False
                break
        if is_swing:
            points.append(SwingPoint(
                index=i,
                date=str(high.index[i]),
                price=float(val),
                kind="high",
            ))
    return points


def detect_swing_lows(
    low: pd.Series,
    order: int = 5,
) -> list[SwingPoint]:
    """Return swing-low points where *low[i]* is below its *order* neighbours.

    Parameters
    ----------
    low : pd.Series
        Series of low prices, indexed by date (or any label).
    order : int
        Number of bars on each side a low must be beneath.
        Must be >= 1.

    Returns
    -------
    list[SwingPoint]
        Detected swing lows in chronological order.
    """
    if order < 1:
        raise ValueError(f"order must be >= 1, got {order}")
    points: list[SwingPoint] = []
    values = low.values
    n = len(values)
    for i in range(order, n - order):
        val = values[i]
        is_swing = True
        for j in range(1, order + 1):
            if values[i - j] <= val or values[i + j] <= val:
                is_swing = False
                break
        if is_swing:
            points.append(SwingPoint(
                index=i,
                date=str(low.index[i]),
                price=float(val),
                kind="low",
            ))
    return points


def detect_swings(
    high: pd.Series,
    low: pd.Series,
    order: int = 5,
) -> list[SwingPoint]:
    """Detect both swing highs and lows, returned in chronological order.

    Parameters
    ----------
    high : pd.Series
        Series of high prices.
    low : pd.Series
        Series of low prices.  Must have the same index as *high*.
    order : int
        Number of bars on each side for swing qualification.

    Returns
    -------
    list[SwingPoint]
        Combined swing highs and lows sorted by bar index.
    """
    highs = detect_swing_highs(high, order=order)
    lows = detect_swing_lows(low, order=order)
    combined = highs + lows
    combined.sort(key=lambda sp: sp.index)
    return combined


# ------------------------------------------------------------------
# Helpers for downstream analysis
# ------------------------------------------------------------------

def swing_highs_series(
    high: pd.Series,
    order: int = 5,
) -> pd.Series:
    """Return a Series with swing-high prices; NaN elsewhere.

    Useful for overlay plotting or vectorised downstream logic.
    """
    result = pd.Series(float("nan"), index=high.index, dtype=float)
    for sp in detect_swing_highs(high, order=order):
        result.iloc[sp.index] = sp.price
    return result


def swing_lows_series(
    low: pd.Series,
    order: int = 5,
) -> pd.Series:
    """Return a Series with swing-low prices; NaN elsewhere.

    Useful for overlay plotting or vectorised downstream logic.
    """
    result = pd.Series(float("nan"), index=low.index, dtype=float)
    for sp in detect_swing_lows(low, order=order):
        result.iloc[sp.index] = sp.price
    return result
