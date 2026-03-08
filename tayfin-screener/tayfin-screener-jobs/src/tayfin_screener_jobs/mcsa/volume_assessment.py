"""Volume quality assessment for MCSA scoring.

Evaluates three volume signals from raw OHLCV data and a volume SMA
indicator value.  Pure computation — no I/O.

Signals (per ADR-01 §3 Volume Quality):
  1. pullback_below_sma  — recent average volume < volume SMA
  2. volume_dryup        — minimum daily volume in lookback is below
                           dryup_threshold_pct of the volume SMA
  3. no_heavy_selling    — no single day's volume exceeds
                           heavy_selling_threshold_pct × volume SMA
                           while the close declined
"""

from __future__ import annotations

from dataclasses import dataclass

from tayfin_screener_jobs.mcsa.config import VolumeSignalConfig


@dataclass(frozen=True, slots=True)
class VolumeAssessment:
    """Result of the three MCSA volume quality signals."""

    pullback_below_sma: bool
    volume_dryup: bool
    no_heavy_selling: bool


def assess_volume(
    ohlcv_rows: list[dict],
    vol_sma_value: float | None,
    cfg: VolumeSignalConfig,
) -> VolumeAssessment | None:
    """Assess volume quality for MCSA.

    Parameters
    ----------
    ohlcv_rows :
        Recent OHLCV candles (must already be sorted ascending by date).
        Each dict has at least ``close``, ``volume``.
    vol_sma_value :
        The latest volume SMA value (from the Indicator API).
    cfg :
        Volume signal configuration (lookback, thresholds).

    Returns
    -------
    VolumeAssessment | None
        ``None`` when there is insufficient data (no rows or no SMA).
    """
    if not ohlcv_rows or vol_sma_value is None or vol_sma_value <= 0:
        return None

    # Take only the most recent `lookback_days` candles
    recent = ohlcv_rows[-cfg.lookback_days :]
    if not recent:
        return None

    volumes = [float(r["volume"]) for r in recent if r.get("volume") is not None]
    if not volumes:
        return None

    # 1. Pullback below SMA — mean recent volume < vol SMA
    avg_volume = sum(volumes) / len(volumes)
    pullback_below_sma = avg_volume < vol_sma_value

    # 2. Volume dry-up — any day's volume below dryup_threshold_pct × SMA
    dryup_threshold = cfg.dryup_threshold_pct * vol_sma_value
    min_volume = min(volumes)
    volume_dryup = min_volume < dryup_threshold

    # 3. No heavy selling — no day with volume > heavy_selling_threshold × SMA
    #    while the close declined from the previous day
    heavy_threshold = cfg.heavy_selling_threshold_pct * vol_sma_value
    no_heavy_selling = True
    for i in range(1, len(recent)):
        prev_close = recent[i - 1].get("close")
        cur_close = recent[i].get("close")
        cur_volume = recent[i].get("volume")
        if prev_close is None or cur_close is None or cur_volume is None:
            continue
        if float(cur_close) < float(prev_close) and float(cur_volume) > heavy_threshold:
            no_heavy_selling = False
            break

    return VolumeAssessment(
        pullback_below_sma=pullback_below_sma,
        volume_dryup=volume_dryup,
        no_heavy_selling=no_heavy_selling,
    )
