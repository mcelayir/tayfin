"""Volume feature extraction for VCP analysis.

Pure computation functions.  No DB, no network — pure math.

Features computed
-----------------
* **volume_dryup** — whether recent average volume has dropped
  significantly relative to the longer-term average, signalling
  institutional accumulation is tapering and the base is maturing.
* **volume_ratio** — ratio of recent average volume to the longer-term
  average.  Values < 1.0 indicate declining interest (bullish for VCP
  base completion).
* **volume_trend** — normalised slope of volume (or vol_sma) over a
  recent window.  Negative = declining volume.
* **volume_contraction_pct** — percentage decline from peak volume to
  the most recent volume in the lookback, measuring how much volume
  has dried up during the base.

All functions accept plain floats or small lists — designed to work with
indicator values fetched from the Indicator API (vol_sma) or raw OHLCV
volume data.
"""

from __future__ import annotations


# ------------------------------------------------------------------
# Volume dry-up detection
# ------------------------------------------------------------------

def compute_volume_ratio(
    recent_avg_volume: float,
    longer_avg_volume: float,
) -> float:
    """Ratio of *recent_avg_volume* to *longer_avg_volume*.

    Returns 0.0 when the longer average is zero.
    Values < 1.0 indicate declining volume (bullish for VCP).
    """
    if longer_avg_volume <= 0:
        return 0.0
    return recent_avg_volume / longer_avg_volume


def is_volume_dryup(
    recent_avg_volume: float,
    longer_avg_volume: float,
    threshold: float = 0.7,
) -> bool:
    """True when recent volume has fallen below *threshold* of the
    longer-term average (default: 70 %).

    A dryup indicates reduced selling pressure — bullish for VCP.
    """
    ratio = compute_volume_ratio(recent_avg_volume, longer_avg_volume)
    return ratio <= threshold


# ------------------------------------------------------------------
# Volume trend
# ------------------------------------------------------------------

def compute_volume_trend(
    volume_values: list[float],
    window: int = 10,
) -> float:
    """Normalised slope of volume over the most recent *window* bars.

    Returns ``(last − first) / first`` using the last *window* values.
    Negative → declining volume.  Returns 0.0 when data is insufficient
    or the first value is zero.
    """
    if len(volume_values) < 2:
        return 0.0
    recent = volume_values[-window:] if len(volume_values) >= window else volume_values
    first = recent[0]
    last = recent[-1]
    if first == 0:
        return 0.0
    return (last - first) / first


# ------------------------------------------------------------------
# Volume contraction from peak
# ------------------------------------------------------------------

def compute_volume_contraction_pct(
    volume_values: list[float],
) -> float:
    """Percentage decline from peak volume to the latest value.

    Returns a value in [0, 1] where 1.0 means volume dropped 100 %
    from its peak.  Returns 0.0 when the list is empty, has one value,
    or the peak is zero.
    """
    if len(volume_values) < 2:
        return 0.0
    peak = max(volume_values)
    if peak <= 0:
        return 0.0
    latest = volume_values[-1]
    return max((peak - latest) / peak, 0.0)


# ------------------------------------------------------------------
# Composite feature dict
# ------------------------------------------------------------------

def extract_volume_features(
    *,
    volume_values: list[float],
    vol_sma_50_values: list[float],
    volume_trend_window: int = 10,
    dryup_threshold: float = 0.7,
) -> dict:
    """Compute all volume features and return as a flat dict.

    Parameters
    ----------
    volume_values : list[float]
        Raw daily volume series (most recent at end).
    vol_sma_50_values : list[float]
        Time-series of vol_sma_50 values (most recent at end).
    volume_trend_window : int
        Window for trend calculation.
    dryup_threshold : float
        Threshold ratio below which volume is considered dried up.
    """
    # Compute recent average (last 10 bars) vs longer average (last 50 bars)
    recent_window = min(10, len(volume_values))
    longer_window = min(50, len(volume_values))
    recent_avg = (
        sum(volume_values[-recent_window:]) / recent_window
        if recent_window > 0
        else 0.0
    )
    longer_avg = (
        sum(volume_values[-longer_window:]) / longer_window
        if longer_window > 0
        else 0.0
    )

    return {
        "volume_ratio": round(compute_volume_ratio(recent_avg, longer_avg), 6),
        "volume_dryup": is_volume_dryup(
            recent_avg, longer_avg, threshold=dryup_threshold,
        ),
        "volume_trend": round(
            compute_volume_trend(vol_sma_50_values, window=volume_trend_window), 6,
        ),
        "volume_contraction_pct": round(
            compute_volume_contraction_pct(volume_values), 6,
        ),
    }
