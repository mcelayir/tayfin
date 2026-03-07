"""Volatility and trend feature extraction for VCP analysis.

Pure computation functions.  No DB, no network — pure math.

Features computed
-----------------
* **atr_trend** — slope of ATR over a recent window, normalised by the
  first ATR value.  Negative means volatility is contracting (bullish
  for VCP).
* **near_52w_high** — whether the current close is within a threshold
  of the 252-day rolling high (Minervini criterion: stock should be
  within 25 % of its 52-week high).
* **pct_from_52w_high** — exact fractional distance from the rolling high.
* **ma_alignment** — whether the moving averages are in bullish order:
  close > SMA-50 > SMA-150 > SMA-200  (Minervini trend template).
* **sma_50_slope** — fractional change of SMA-50 over the last *n* bars,
  positive means uptrend.

All functions accept plain floats or small lists — they are designed to
work with the already-computed indicator values fetched from the Indicator
API, **not** raw OHLCV.
"""

from __future__ import annotations


# ------------------------------------------------------------------
# ATR trend
# ------------------------------------------------------------------

def compute_atr_trend(
    atr_values: list[float],
    window: int = 10,
) -> float:
    """Normalised slope of the ATR series over the most recent *window* bars.

    Returns ``(atr_last - atr_first) / atr_first`` using the last *window*
    values.  A negative result indicates contracting volatility.

    Returns 0.0 when there are fewer than 2 values or the first ATR is zero.
    """
    if len(atr_values) < 2:
        return 0.0
    recent = atr_values[-window:] if len(atr_values) >= window else atr_values
    first = recent[0]
    last = recent[-1]
    if first == 0:
        return 0.0
    return (last - first) / first


# ------------------------------------------------------------------
# 52-week high proximity
# ------------------------------------------------------------------

def compute_pct_from_high(
    current_close: float,
    rolling_high_252: float,
) -> float:
    """Fractional distance of *current_close* from the 252-day rolling high.

    Returns a value in [0, 1+] where 0 means at the high and 0.25 means
    25 % below.  Returns 0.0 when the rolling high is zero.
    """
    if rolling_high_252 <= 0:
        return 0.0
    return max((rolling_high_252 - current_close) / rolling_high_252, 0.0)


def is_near_52w_high(
    current_close: float,
    rolling_high_252: float,
    threshold: float = 0.25,
) -> bool:
    """True when *current_close* is within *threshold* (default 25 %)
    of the 252-day rolling high.
    """
    return compute_pct_from_high(current_close, rolling_high_252) <= threshold


# ------------------------------------------------------------------
# Moving-average alignment (Minervini trend template)
# ------------------------------------------------------------------

def is_ma_aligned(
    current_close: float,
    sma_50: float,
    sma_150: float,
    sma_200: float,
) -> bool:
    """Bullish Minervini alignment: close > SMA-50 > SMA-150 > SMA-200."""
    return current_close > sma_50 > sma_150 > sma_200


def compute_sma_50_slope(
    sma_50_values: list[float],
    window: int = 20,
) -> float:
    """Fractional change of SMA-50 over the last *window* bars.

    Positive → uptrend.  Returns 0.0 when data is insufficient.
    """
    if len(sma_50_values) < 2:
        return 0.0
    recent = sma_50_values[-window:] if len(sma_50_values) >= window else sma_50_values
    first = recent[0]
    last = recent[-1]
    if first == 0:
        return 0.0
    return (last - first) / first


# ------------------------------------------------------------------
# Composite feature dict
# ------------------------------------------------------------------

def extract_volatility_features(
    *,
    current_close: float,
    sma_50: float,
    sma_150: float,
    sma_200: float,
    rolling_high_252: float,
    atr_values: list[float],
    sma_50_values: list[float],
    atr_trend_window: int = 10,
    sma_slope_window: int = 20,
    near_high_threshold: float = 0.25,
) -> dict:
    """Compute all volatility / trend features and return as a flat dict.

    This is the primary entry-point called by the VCP screen job to
    assemble the volatility portion of ``features_json``.
    """
    pct_from_high = compute_pct_from_high(current_close, rolling_high_252)
    return {
        "atr_trend": round(compute_atr_trend(atr_values, window=atr_trend_window), 6),
        "pct_from_52w_high": round(pct_from_high, 6),
        "near_52w_high": is_near_52w_high(
            current_close, rolling_high_252, threshold=near_high_threshold,
        ),
        "ma_alignment": is_ma_aligned(current_close, sma_50, sma_150, sma_200),
        "sma_50_slope": round(compute_sma_50_slope(sma_50_values, window=sma_slope_window), 6),
    }
