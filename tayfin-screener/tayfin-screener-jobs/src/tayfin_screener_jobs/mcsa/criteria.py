"""MCSA criteria — pure functions for the 8 Minervini Trend Template checks.

Each criterion function accepts precomputed values and returns a boolean.
Pure math — no DB, no network.

See docs/research/mcsa_trend_template_spec.md for the canonical reference.
"""

from __future__ import annotations


def criterion_1(close: float, sma_200: float, sma_200_slope: float) -> bool:
    """Price > SMA-200 AND SMA-200 is trending up (positive slope).

    "SMA-200 trending up for at least 1 month" is quantified as a
    positive slope over 20 trading days (slope_period=20).
    """
    return close > sma_200 and sma_200_slope > 0


def criterion_2(sma_150: float, sma_200: float) -> bool:
    """SMA-150 > SMA-200."""
    return sma_150 > sma_200


def criterion_3(sma_50: float, sma_150: float, sma_200: float) -> bool:
    """SMA-50 > SMA-150 AND SMA-50 > SMA-200."""
    return sma_50 > sma_150 and sma_50 > sma_200


def criterion_4(close: float, sma_50: float) -> bool:
    """Price > SMA-50."""
    return close > sma_50


def criterion_5(close: float, rolling_low_252: float) -> bool:
    """Price ≥ 1.25 × 52-week low (at least 25% above)."""
    return close >= 1.25 * rolling_low_252


def criterion_6(close: float, rolling_high_252: float) -> bool:
    """Price ≥ 0.75 × 52-week high (within 25% of high)."""
    return close >= 0.75 * rolling_high_252


def criterion_7(rs_rank: float, threshold: float = 70.0) -> bool:
    """RS ranking > threshold (default 70 = top 30th percentile)."""
    return rs_rank > threshold


def criterion_8(
    recent_closes: list[float],
    recent_sma_50: list[float],
    min_days_above: int = 5,
) -> bool:
    """Price above SMA-50 for at least *min_days_above* of the last N days.

    PROXY for "price trading above SMA-50 after forming a sound base".
    This is a Phase 0 quantifiable approximation — see ADR-0001 §D5.

    Args:
        recent_closes: Last N trading days of close prices (newest first).
        recent_sma_50: Last N trading days of SMA-50 values (newest first).
        min_days_above: Minimum days the close must be above SMA-50.
    """
    if len(recent_closes) != len(recent_sma_50):
        raise ValueError(
            f"recent_closes ({len(recent_closes)}) and recent_sma_50 "
            f"({len(recent_sma_50)}) must have the same length"
        )
    days_above = sum(1 for c, s in zip(recent_closes, recent_sma_50) if c > s)
    return days_above >= min_days_above
