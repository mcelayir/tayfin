"""MCSA evaluation — orchestrates the 8 criteria into a single result.

Pure computation — no DB, no network.

See docs/research/mcsa_trend_template_spec.md for the canonical reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .criteria import (
    criterion_1,
    criterion_2,
    criterion_3,
    criterion_4,
    criterion_5,
    criterion_6,
    criterion_7,
    criterion_8,
)


@dataclass
class McsaResult:
    """Result of evaluating the 8 Minervini Trend Template criteria."""

    ticker: str
    as_of_date: date
    mcsa_pass: bool
    criteria_json: dict
    rs_rank: float
    criteria_count_pass: int


def evaluate_mcsa(
    *,
    ticker: str,
    as_of_date: date,
    close: float,
    sma_50: float,
    sma_150: float,
    sma_200: float,
    sma_200_slope: float,
    rolling_high_252: float,
    rolling_low_252: float,
    rs_rank: float,
    recent_closes: list[float],
    recent_sma_50: list[float],
) -> McsaResult:
    """Evaluate all 8 MCSA criteria and return a structured result.

    All inputs are precomputed values — this function performs no I/O.

    Args:
        ticker: Stock ticker symbol.
        as_of_date: The evaluation date.
        close: Latest closing price.
        sma_50: 50-day simple moving average.
        sma_150: 150-day simple moving average.
        sma_200: 200-day simple moving average.
        sma_200_slope: Slope of SMA-200 over 20 bars (from indicator_series).
        rolling_high_252: 252-day rolling maximum of close.
        rolling_low_252: 252-day rolling minimum of close.
        rs_rank: Relative strength percentile rank (0-100, computed in screener).
        recent_closes: Last 10 trading days of close prices (newest first).
        recent_sma_50: Last 10 trading days of SMA-50 values (newest first).
    """
    c1 = criterion_1(close, sma_200, sma_200_slope)
    c2 = criterion_2(sma_150, sma_200)
    c3 = criterion_3(sma_50, sma_150, sma_200)
    c4 = criterion_4(close, sma_50)
    c5 = criterion_5(close, rolling_low_252)
    c6 = criterion_6(close, rolling_high_252)
    c7 = criterion_7(rs_rank)
    c8 = criterion_8(recent_closes, recent_sma_50)

    criteria_json = {
        "c1_sma200_trending_up_and_price_above": c1,
        "c2_sma150_above_sma200": c2,
        "c3_sma50_above_sma150_and_sma200": c3,
        "c4_price_above_sma50": c4,
        "c5_price_25pct_above_52w_low": c5,
        "c6_price_within_25pct_of_52w_high": c6,
        "c7_rs_rank_above_70": c7,
        "c8_price_above_sma50_sound_base": c8,
    }

    results = [c1, c2, c3, c4, c5, c6, c7, c8]
    criteria_count_pass = sum(results)
    mcsa_pass = all(results)

    return McsaResult(
        ticker=ticker,
        as_of_date=as_of_date,
        mcsa_pass=mcsa_pass,
        criteria_json=criteria_json,
        rs_rank=rs_rank,
        criteria_count_pass=criteria_count_pass,
    )
