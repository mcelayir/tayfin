"""Tests for volatility and trend feature extraction."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.vcp.volatility_features import (
    compute_atr_trend,
    compute_pct_from_high,
    compute_sma_50_slope,
    extract_volatility_features,
    is_ma_aligned,
    is_near_52w_high,
)


# ------------------------------------------------------------------
# compute_atr_trend
# ------------------------------------------------------------------

class TestComputeAtrTrend:
    def test_contracting_atr(self):
        """Decreasing ATR → negative trend (bullish for VCP)."""
        atr = [5.0, 4.5, 4.0, 3.5, 3.0]
        result = compute_atr_trend(atr, window=5)
        # (3.0 - 5.0) / 5.0 = -0.4
        assert abs(result - (-0.4)) < 1e-9

    def test_expanding_atr(self):
        """Increasing ATR → positive trend."""
        atr = [3.0, 3.5, 4.0, 4.5, 5.0]
        result = compute_atr_trend(atr, window=5)
        # (5.0 - 3.0) / 3.0 ≈ 0.6667
        assert abs(result - (2.0 / 3.0)) < 1e-9

    def test_flat_atr(self):
        atr = [4.0, 4.0, 4.0, 4.0]
        assert compute_atr_trend(atr) == 0.0

    def test_window_clips_to_recent(self):
        """When series is longer than window, only use last N."""
        atr = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        result = compute_atr_trend(atr, window=3)
        # last 3: [4.0, 3.0] wait — last 3 values: [5.0, 4.0, 3.0]
        # (3.0 - 5.0) / 5.0 = -0.4
        assert abs(result - (-0.4)) < 1e-9

    def test_single_value_returns_zero(self):
        assert compute_atr_trend([5.0]) == 0.0

    def test_empty_returns_zero(self):
        assert compute_atr_trend([]) == 0.0

    def test_first_zero_returns_zero(self):
        assert compute_atr_trend([0.0, 5.0, 3.0]) == 0.0


# ------------------------------------------------------------------
# compute_pct_from_high
# ------------------------------------------------------------------

class TestComputePctFromHigh:
    def test_at_high(self):
        assert compute_pct_from_high(100.0, 100.0) == 0.0

    def test_10_pct_below(self):
        result = compute_pct_from_high(90.0, 100.0)
        assert abs(result - 0.10) < 1e-9

    def test_25_pct_below(self):
        result = compute_pct_from_high(75.0, 100.0)
        assert abs(result - 0.25) < 1e-9

    def test_above_high_returns_zero(self):
        """Close above rolling high (due to lag) → 0.0 (clamped)."""
        assert compute_pct_from_high(105.0, 100.0) == 0.0

    def test_zero_high_returns_zero(self):
        assert compute_pct_from_high(50.0, 0.0) == 0.0

    def test_negative_high_returns_zero(self):
        assert compute_pct_from_high(50.0, -10.0) == 0.0


# ------------------------------------------------------------------
# is_near_52w_high
# ------------------------------------------------------------------

class TestIsNear52wHigh:
    def test_within_threshold(self):
        assert is_near_52w_high(80.0, 100.0, threshold=0.25) is True

    def test_exactly_at_threshold(self):
        assert is_near_52w_high(75.0, 100.0, threshold=0.25) is True

    def test_beyond_threshold(self):
        assert is_near_52w_high(74.0, 100.0, threshold=0.25) is False

    def test_at_high(self):
        assert is_near_52w_high(100.0, 100.0) is True

    def test_custom_threshold(self):
        assert is_near_52w_high(85.0, 100.0, threshold=0.10) is False
        assert is_near_52w_high(91.0, 100.0, threshold=0.10) is True


# ------------------------------------------------------------------
# is_ma_aligned
# ------------------------------------------------------------------

class TestIsMaAligned:
    def test_bullish_alignment(self):
        assert is_ma_aligned(180.0, 175.0, 170.0, 165.0) is True

    def test_close_below_sma50(self):
        assert is_ma_aligned(170.0, 175.0, 170.0, 165.0) is False

    def test_sma50_below_sma150(self):
        assert is_ma_aligned(180.0, 168.0, 170.0, 165.0) is False

    def test_sma150_below_sma200(self):
        assert is_ma_aligned(180.0, 175.0, 160.0, 165.0) is False

    def test_all_equal_is_false(self):
        """Equal values are NOT strictly greater → False."""
        assert is_ma_aligned(100.0, 100.0, 100.0, 100.0) is False


# ------------------------------------------------------------------
# compute_sma_50_slope
# ------------------------------------------------------------------

class TestComputeSma50Slope:
    def test_uptrend(self):
        sma = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = compute_sma_50_slope(sma, window=5)
        # (104 - 100) / 100 = 0.04
        assert abs(result - 0.04) < 1e-9

    def test_downtrend(self):
        sma = [100.0, 99.0, 98.0, 97.0, 96.0]
        result = compute_sma_50_slope(sma, window=5)
        assert abs(result - (-0.04)) < 1e-9

    def test_flat(self):
        sma = [100.0, 100.0, 100.0]
        assert compute_sma_50_slope(sma) == 0.0

    def test_window_clips(self):
        sma = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        result = compute_sma_50_slope(sma, window=3)
        # last 3: [80.0, 90.0, 100.0] → (100 - 80) / 80 = 0.25
        assert abs(result - 0.25) < 1e-9

    def test_single_value(self):
        assert compute_sma_50_slope([100.0]) == 0.0

    def test_empty(self):
        assert compute_sma_50_slope([]) == 0.0


# ------------------------------------------------------------------
# extract_volatility_features (composite)
# ------------------------------------------------------------------

class TestExtractVolatilityFeatures:
    def test_bullish_vcp_candidate(self):
        """Typical bullish VCP candidate: contracting ATR, near high, aligned MAs."""
        result = extract_volatility_features(
            current_close=175.0,
            sma_50=170.0,
            sma_150=165.0,
            sma_200=160.0,
            rolling_high_252=180.0,
            atr_values=[5.0, 4.5, 4.0, 3.5, 3.0],
            sma_50_values=[160.0, 163.0, 166.0, 168.0, 170.0],
        )
        assert result["atr_trend"] < 0  # contracting
        assert result["near_52w_high"] is True
        assert result["ma_alignment"] is True
        assert result["sma_50_slope"] > 0  # uptrend
        assert 0 < result["pct_from_52w_high"] < 0.05

    def test_bearish_stock(self):
        """Stock in downtrend: expanding ATR, far from high, mis-aligned MAs."""
        result = extract_volatility_features(
            current_close=60.0,
            sma_50=70.0,
            sma_150=80.0,
            sma_200=90.0,
            rolling_high_252=100.0,
            atr_values=[2.0, 3.0, 4.0, 5.0, 6.0],
            sma_50_values=[80.0, 78.0, 75.0, 72.0, 70.0],
        )
        assert result["atr_trend"] > 0  # expanding
        assert result["near_52w_high"] is False
        assert result["ma_alignment"] is False
        assert result["sma_50_slope"] < 0  # downtrend
        assert result["pct_from_52w_high"] == 0.4

    def test_all_keys_present(self):
        result = extract_volatility_features(
            current_close=100.0,
            sma_50=95.0,
            sma_150=90.0,
            sma_200=85.0,
            rolling_high_252=110.0,
            atr_values=[3.0, 3.0],
            sma_50_values=[95.0, 95.0],
        )
        expected_keys = {
            "atr_trend", "pct_from_52w_high", "near_52w_high",
            "ma_alignment", "sma_50_slope",
        }
        assert set(result.keys()) == expected_keys

    def test_values_are_rounded(self):
        result = extract_volatility_features(
            current_close=100.0,
            sma_50=99.0,
            sma_150=98.0,
            sma_200=97.0,
            rolling_high_252=103.0,
            atr_values=[3.333333, 2.666666],
            sma_50_values=[98.123456, 99.0],
        )
        # Floats should be rounded to 6 decimal places
        assert isinstance(result["atr_trend"], float)
        atr_str = str(result["atr_trend"])
        # At most 6 decimal digits (may have fewer)
        if "." in atr_str:
            assert len(atr_str.split(".")[1]) <= 7  # repr may add one extra

    def test_custom_windows(self):
        """Custom atr_trend_window and sma_slope_window are respected."""
        atr = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0]
        sma = [90.0, 92.0, 94.0, 96.0, 98.0, 100.0]
        r1 = extract_volatility_features(
            current_close=100.0, sma_50=100.0, sma_150=95.0, sma_200=90.0,
            rolling_high_252=105.0,
            atr_values=atr, sma_50_values=sma,
            atr_trend_window=3, sma_slope_window=3,
        )
        r2 = extract_volatility_features(
            current_close=100.0, sma_50=100.0, sma_150=95.0, sma_200=90.0,
            rolling_high_252=105.0,
            atr_values=atr, sma_50_values=sma,
            atr_trend_window=6, sma_slope_window=6,
        )
        # Different windows should generally give different results
        # (unless data happens to line up, which it doesn't here)
        assert r1["atr_trend"] != r2["atr_trend"]
