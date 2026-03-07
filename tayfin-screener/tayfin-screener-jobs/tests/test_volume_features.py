"""Tests for volume feature extraction."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.vcp.volume_features import (
    compute_volume_contraction_pct,
    compute_volume_ratio,
    compute_volume_trend,
    extract_volume_features,
    is_volume_dryup,
)


# ------------------------------------------------------------------
# compute_volume_ratio
# ------------------------------------------------------------------

class TestComputeVolumeRatio:
    def test_equal_volumes(self):
        assert compute_volume_ratio(1_000_000, 1_000_000) == 1.0

    def test_recent_lower(self):
        result = compute_volume_ratio(500_000, 1_000_000)
        assert abs(result - 0.5) < 1e-9

    def test_recent_higher(self):
        result = compute_volume_ratio(1_500_000, 1_000_000)
        assert abs(result - 1.5) < 1e-9

    def test_longer_zero(self):
        assert compute_volume_ratio(500_000, 0) == 0.0

    def test_longer_negative(self):
        assert compute_volume_ratio(500_000, -100) == 0.0

    def test_both_zero(self):
        assert compute_volume_ratio(0, 0) == 0.0


# ------------------------------------------------------------------
# is_volume_dryup
# ------------------------------------------------------------------

class TestIsVolumeDryup:
    def test_below_threshold(self):
        assert is_volume_dryup(600_000, 1_000_000, threshold=0.7) is True

    def test_at_threshold(self):
        assert is_volume_dryup(700_000, 1_000_000, threshold=0.7) is True

    def test_above_threshold(self):
        assert is_volume_dryup(800_000, 1_000_000, threshold=0.7) is False

    def test_equal_volumes_not_dryup(self):
        assert is_volume_dryup(1_000_000, 1_000_000, threshold=0.7) is False

    def test_custom_threshold(self):
        assert is_volume_dryup(450_000, 1_000_000, threshold=0.5) is True
        assert is_volume_dryup(550_000, 1_000_000, threshold=0.5) is False


# ------------------------------------------------------------------
# compute_volume_trend
# ------------------------------------------------------------------

class TestComputeVolumeTrend:
    def test_declining_volume(self):
        vol = [1_000_000, 900_000, 800_000, 700_000, 600_000]
        result = compute_volume_trend(vol, window=5)
        # (600k - 1M) / 1M = -0.4
        assert abs(result - (-0.4)) < 1e-9

    def test_rising_volume(self):
        vol = [600_000, 700_000, 800_000, 900_000, 1_000_000]
        result = compute_volume_trend(vol, window=5)
        # (1M - 600k) / 600k ≈ 0.6667
        assert abs(result - (400_000 / 600_000)) < 1e-9

    def test_flat_volume(self):
        vol = [1_000_000, 1_000_000, 1_000_000]
        assert compute_volume_trend(vol) == 0.0

    def test_window_clips(self):
        vol = [2_000_000, 1_500_000, 1_000_000, 800_000, 600_000, 500_000]
        result = compute_volume_trend(vol, window=3)
        # last 3: [800k, 600k, 500k] → (500k - 800k) / 800k = -0.375
        assert abs(result - (-0.375)) < 1e-9

    def test_single_value(self):
        assert compute_volume_trend([1_000_000]) == 0.0

    def test_empty(self):
        assert compute_volume_trend([]) == 0.0

    def test_first_zero(self):
        assert compute_volume_trend([0, 500_000, 1_000_000]) == 0.0


# ------------------------------------------------------------------
# compute_volume_contraction_pct
# ------------------------------------------------------------------

class TestComputeVolumeContractionPct:
    def test_50_pct_decline(self):
        vol = [1_000_000, 800_000, 600_000, 500_000]
        result = compute_volume_contraction_pct(vol)
        # peak=1M, latest=500k → (1M - 500k) / 1M = 0.5
        assert abs(result - 0.5) < 1e-9

    def test_at_peak(self):
        vol = [500_000, 800_000, 1_000_000]
        result = compute_volume_contraction_pct(vol)
        # peak=1M, latest=1M → 0
        assert result == 0.0

    def test_no_decline(self):
        vol = [100_000, 200_000, 300_000]
        result = compute_volume_contraction_pct(vol)
        # peak=300k, latest=300k → 0
        assert result == 0.0

    def test_full_decline(self):
        vol = [1_000_000, 500_000, 0]
        result = compute_volume_contraction_pct(vol)
        assert abs(result - 1.0) < 1e-9

    def test_single_value(self):
        assert compute_volume_contraction_pct([1_000_000]) == 0.0

    def test_empty(self):
        assert compute_volume_contraction_pct([]) == 0.0

    def test_all_zeros(self):
        assert compute_volume_contraction_pct([0, 0, 0]) == 0.0

    def test_peak_in_middle(self):
        vol = [200_000, 500_000, 1_000_000, 700_000, 400_000]
        result = compute_volume_contraction_pct(vol)
        # peak=1M, latest=400k → 0.6
        assert abs(result - 0.6) < 1e-9


# ------------------------------------------------------------------
# extract_volume_features (composite)
# ------------------------------------------------------------------

class TestExtractVolumeFeatures:
    def test_dryup_scenario(self):
        """Volume dried up significantly → dryup True, low ratio."""
        volume = [1_000_000] * 40 + [400_000] * 10  # big drop in last 10
        vol_sma_values = [900_000, 850_000, 800_000, 700_000, 600_000]
        result = extract_volume_features(
            volume_values=volume,
            vol_sma_50_values=vol_sma_values,
        )
        assert result["volume_dryup"] is True
        assert result["volume_ratio"] < 1.0
        assert result["volume_trend"] < 0
        assert result["volume_contraction_pct"] > 0

    def test_active_volume(self):
        """Volume staying high → no dryup."""
        volume = [1_000_000] * 50
        vol_sma_values = [1_000_000] * 10
        result = extract_volume_features(
            volume_values=volume,
            vol_sma_50_values=vol_sma_values,
        )
        assert result["volume_dryup"] is False
        assert abs(result["volume_ratio"] - 1.0) < 1e-6
        assert result["volume_trend"] == 0.0

    def test_all_keys_present(self):
        result = extract_volume_features(
            volume_values=[100_000, 90_000, 80_000],
            vol_sma_50_values=[95_000, 90_000, 85_000],
        )
        expected_keys = {
            "volume_ratio", "volume_dryup", "volume_trend",
            "volume_contraction_pct",
        }
        assert set(result.keys()) == expected_keys

    def test_values_are_rounded(self):
        result = extract_volume_features(
            volume_values=[333_333, 222_222, 111_111],
            vol_sma_50_values=[333_333, 222_222, 111_111],
        )
        for key in ("volume_ratio", "volume_trend", "volume_contraction_pct"):
            val = result[key]
            assert isinstance(val, float)
            s = str(val)
            if "." in s:
                assert len(s.split(".")[1]) <= 7

    def test_custom_windows(self):
        volume = [1_000_000, 800_000, 600_000, 400_000, 200_000]
        vol_sma = [900_000, 700_000, 500_000, 300_000, 200_000]
        r1 = extract_volume_features(
            volume_values=volume, vol_sma_50_values=vol_sma, volume_trend_window=3,
        )
        r2 = extract_volume_features(
            volume_values=volume, vol_sma_50_values=vol_sma, volume_trend_window=5,
        )
        assert r1["volume_trend"] != r2["volume_trend"]

    def test_short_volume_list(self):
        """Short input doesn't crash."""
        result = extract_volume_features(
            volume_values=[500_000],
            vol_sma_50_values=[500_000],
        )
        assert result["volume_dryup"] is False
        assert result["volume_contraction_pct"] == 0.0
