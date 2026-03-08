"""Tests for tayfin_screener_jobs.mcsa.volume_assessment."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.mcsa.config import VolumeSignalConfig
from tayfin_screener_jobs.mcsa.volume_assessment import (
    VolumeAssessment,
    assess_volume,
)


# ===================================================================
# Helpers
# ===================================================================

def _default_vol_cfg() -> VolumeSignalConfig:
    return VolumeSignalConfig()


def _make_ohlcv(
    n: int = 20,
    *,
    base_volume: int = 1_000_000,
    base_close: float = 100.0,
) -> list[dict]:
    """Build *n* ascending-date OHLCV rows with stable volume/close."""
    from datetime import date, timedelta

    base = date.today() - timedelta(days=n)
    rows = []
    for i in range(n):
        rows.append({
            "as_of_date": (base + timedelta(days=i)).isoformat(),
            "open": base_close + i * 0.1,
            "high": base_close + i * 0.1 + 2,
            "low": base_close + i * 0.1 - 2,
            "close": base_close + i * 0.1,
            "volume": base_volume,
        })
    return rows


# ===================================================================
# TestVolumeAssessment dataclass
# ===================================================================

class TestVolumeAssessmentDataclass:
    def test_frozen(self):
        va = VolumeAssessment(
            pullback_below_sma=True, volume_dryup=False, no_heavy_selling=True,
        )
        with pytest.raises(AttributeError):
            va.pullback_below_sma = False  # type: ignore[misc]

    def test_fields(self):
        va = VolumeAssessment(
            pullback_below_sma=True, volume_dryup=True, no_heavy_selling=False,
        )
        assert va.pullback_below_sma is True
        assert va.volume_dryup is True
        assert va.no_heavy_selling is False


# ===================================================================
# TestAssessVolume — edge cases
# ===================================================================

class TestAssessVolumeEdgeCases:
    """Boundary / guard-clause tests."""

    def test_empty_rows_returns_none(self):
        assert assess_volume([], 1_000_000.0, _default_vol_cfg()) is None

    def test_none_vol_sma_returns_none(self):
        rows = _make_ohlcv(5)
        assert assess_volume(rows, None, _default_vol_cfg()) is None

    def test_zero_vol_sma_returns_none(self):
        rows = _make_ohlcv(5)
        assert assess_volume(rows, 0.0, _default_vol_cfg()) is None

    def test_negative_vol_sma_returns_none(self):
        rows = _make_ohlcv(5)
        assert assess_volume(rows, -100.0, _default_vol_cfg()) is None


# ===================================================================
# TestPullbackBelowSma
# ===================================================================

class TestPullbackBelowSma:
    """Signal 1: mean recent volume < volume SMA."""

    def test_avg_below_sma(self):
        """avg vol = 500k, SMA = 1M → pullback."""
        rows = _make_ohlcv(20, base_volume=500_000)
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.pullback_below_sma is True

    def test_avg_above_sma(self):
        """avg vol = 2M, SMA = 1M → no pullback."""
        rows = _make_ohlcv(20, base_volume=2_000_000)
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.pullback_below_sma is False


# ===================================================================
# TestVolumeDryup
# ===================================================================

class TestVolumeDryup:
    """Signal 2: min volume < dryup_threshold_pct × SMA."""

    def test_dryup_detected(self):
        """min vol = 100k, threshold = 0.5 × 1M = 500k → dryup."""
        rows = _make_ohlcv(20, base_volume=1_000_000)
        # Make one day extremely low
        rows[10]["volume"] = 100_000
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.volume_dryup is True

    def test_no_dryup(self):
        """All volumes at 800k, threshold = 0.5 × 1M = 500k → no dryup."""
        rows = _make_ohlcv(20, base_volume=800_000)
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.volume_dryup is False


# ===================================================================
# TestNoHeavySelling
# ===================================================================

class TestNoHeavySelling:
    """Signal 3: no day with volume > heavy_threshold AND declining close."""

    def test_no_heavy_selling(self):
        """All volumes normal, prices rising → no heavy selling."""
        rows = _make_ohlcv(20, base_volume=500_000)
        # Ensure prices are strictly ascending
        for i, r in enumerate(rows):
            r["close"] = 100.0 + i
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.no_heavy_selling is True

    def test_heavy_selling_detected(self):
        """A day with volume > 1.5 × SMA while close declined."""
        rows = _make_ohlcv(20, base_volume=500_000)
        # Make day 10 have high volume + declining close
        rows[10]["volume"] = 2_000_000  # > 1.5 × 1M = 1.5M
        rows[10]["close"] = 95.0
        rows[9]["close"] = 100.0
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.no_heavy_selling is False

    def test_high_volume_but_close_up_is_not_selling(self):
        """High volume day but close didn't decline → no heavy selling."""
        rows = _make_ohlcv(20, base_volume=500_000)
        for i, r in enumerate(rows):
            r["close"] = 100.0 + i
        rows[10]["volume"] = 2_000_000  # high volume
        rows[10]["close"] = 115.0  # but close is UP
        rows[9]["close"] = 110.0
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.no_heavy_selling is True


# ===================================================================
# TestLookbackWindow
# ===================================================================

class TestLookbackWindow:
    """Tests that only lookback_days worth of data is used."""

    def test_uses_only_recent_candles(self):
        """Config with lookback_days=5 should only look at last 5 rows."""
        cfg = VolumeSignalConfig(lookback_days=5)
        rows = _make_ohlcv(30, base_volume=800_000)
        # Make an early row have extreme volume — should be ignored
        rows[0]["volume"] = 100  # outside lookback window
        result = assess_volume(rows, 1_000_000.0, cfg)
        assert result is not None
        # min vol in last 5 = 800k, threshold = 0.5 × 1M = 500k → no dryup
        assert result.volume_dryup is False


# ===================================================================
# TestCompositeResult
# ===================================================================

class TestCompositeResult:
    """End-to-end assessment returning all three signals."""

    def test_all_signals_true(self):
        """Low avg vol, one very low day, no selling → all True."""
        rows = _make_ohlcv(20, base_volume=400_000)
        for i, r in enumerate(rows):
            r["close"] = 100.0 + i  # ascending
        rows[5]["volume"] = 50_000  # dryup trigger
        result = assess_volume(rows, 1_000_000.0, _default_vol_cfg())
        assert result is not None
        assert result.pullback_below_sma is True
        assert result.volume_dryup is True
        assert result.no_heavy_selling is True
