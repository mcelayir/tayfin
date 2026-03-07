"""Tests for swing detection logic."""

from __future__ import annotations

import pandas as pd
import pytest

from tayfin_screener_jobs.vcp.swing_detection import (
    SwingPoint,
    detect_swing_highs,
    detect_swing_lows,
    detect_swings,
    swing_highs_series,
    swing_lows_series,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _date_index(n: int, start: str = "2025-01-01") -> pd.DatetimeIndex:
    """Generate a date index of *n* business days."""
    return pd.bdate_range(start=start, periods=n)


# ------------------------------------------------------------------
# detect_swing_highs
# ------------------------------------------------------------------

class TestDetectSwingHighs:
    """Tests for detect_swing_highs."""

    def test_single_peak_order1(self):
        """Clear single peak detected with order=1."""
        #  prices: 1, 2, 5, 2, 1
        high = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0], index=_date_index(5))
        result = detect_swing_highs(high, order=1)
        assert len(result) == 1
        sp = result[0]
        assert sp.index == 2
        assert sp.price == 5.0
        assert sp.kind == "high"

    def test_single_peak_order2(self):
        """Peak at index 3 dominates 2 bars on each side."""
        # 1, 2, 3, 10, 3, 2, 1
        high = pd.Series([1, 2, 3, 10, 3, 2, 1], dtype=float, index=_date_index(7))
        result = detect_swing_highs(high, order=2)
        assert len(result) == 1
        assert result[0].index == 3
        assert result[0].price == 10.0

    def test_multiple_peaks(self):
        """Two separate peaks."""
        #  index: 0  1  2  3  4  5  6  7  8  9 10
        high = pd.Series(
            [1, 3, 5, 3, 1, 1, 1, 4, 8, 4, 1],
            dtype=float,
            index=_date_index(11),
        )
        result = detect_swing_highs(high, order=2)
        assert len(result) == 2
        assert result[0].index == 2
        assert result[0].price == 5.0
        assert result[1].index == 8
        assert result[1].price == 8.0

    def test_plateau_not_detected(self):
        """Equal values (plateau) should NOT be swing highs (strict >)."""
        high = pd.Series([1, 5, 5, 5, 1], dtype=float, index=_date_index(5))
        result = detect_swing_highs(high, order=1)
        assert len(result) == 0

    def test_monotonic_no_swings(self):
        """Monotonically increasing data has no swing highs."""
        high = pd.Series(range(1, 21), dtype=float, index=_date_index(20))
        result = detect_swing_highs(high, order=3)
        assert len(result) == 0

    def test_too_short_for_order(self):
        """Series shorter than 2*order+1 yields no results."""
        high = pd.Series([1, 5, 1], dtype=float, index=_date_index(3))
        result = detect_swing_highs(high, order=2)
        assert len(result) == 0

    def test_invalid_order_raises(self):
        high = pd.Series([1, 2, 3], dtype=float, index=_date_index(3))
        with pytest.raises(ValueError, match="order must be >= 1"):
            detect_swing_highs(high, order=0)

    def test_date_field_populated(self):
        """SwingPoint.date should be the ISO date of the bar."""
        dates = pd.to_datetime(["2025-06-01", "2025-06-02", "2025-06-03"])
        high = pd.Series([1.0, 10.0, 1.0], index=dates)
        result = detect_swing_highs(high, order=1)
        assert len(result) == 1
        assert "2025-06-02" in result[0].date


# ------------------------------------------------------------------
# detect_swing_lows
# ------------------------------------------------------------------

class TestDetectSwingLows:
    """Tests for detect_swing_lows."""

    def test_single_trough_order1(self):
        """Clear single trough detected with order=1."""
        low = pd.Series([5.0, 2.0, 1.0, 2.0, 5.0], index=_date_index(5))
        result = detect_swing_lows(low, order=1)
        assert len(result) == 1
        sp = result[0]
        assert sp.index == 2
        assert sp.price == 1.0
        assert sp.kind == "low"

    def test_single_trough_order2(self):
        """Trough at index 3 dominates 2 bars on each side."""
        low = pd.Series([10, 8, 5, 1, 5, 8, 10], dtype=float, index=_date_index(7))
        result = detect_swing_lows(low, order=2)
        assert len(result) == 1
        assert result[0].index == 3
        assert result[0].price == 1.0

    def test_multiple_troughs(self):
        """Two separate troughs."""
        low = pd.Series(
            [10, 5, 2, 5, 10, 10, 10, 6, 1, 6, 10],
            dtype=float,
            index=_date_index(11),
        )
        result = detect_swing_lows(low, order=2)
        assert len(result) == 2
        assert result[0].index == 2
        assert result[0].price == 2.0
        assert result[1].index == 8
        assert result[1].price == 1.0

    def test_plateau_not_detected(self):
        """Equal values should NOT be swing lows (strict <)."""
        low = pd.Series([5, 1, 1, 1, 5], dtype=float, index=_date_index(5))
        result = detect_swing_lows(low, order=1)
        assert len(result) == 0

    def test_monotonic_no_swings(self):
        """Monotonically decreasing data has no swing lows."""
        low = pd.Series(range(20, 0, -1), dtype=float, index=_date_index(20))
        result = detect_swing_lows(low, order=3)
        assert len(result) == 0

    def test_invalid_order_raises(self):
        low = pd.Series([1, 2, 3], dtype=float, index=_date_index(3))
        with pytest.raises(ValueError, match="order must be >= 1"):
            detect_swing_lows(low, order=-1)


# ------------------------------------------------------------------
# detect_swings (combined)
# ------------------------------------------------------------------

class TestDetectSwings:
    """Tests for detect_swings (combined highs + lows)."""

    def test_combined_chronological_order(self):
        """Swing highs and lows should be interleaved by bar index."""
        # Construct a simple wave: peak at 2, trough at 4, peak at 6
        high = pd.Series(
            [1, 3, 10, 3, 1, 3, 10, 3, 1],
            dtype=float,
            index=_date_index(9),
        )
        low = pd.Series(
            [5, 5, 5, 5, 1, 5, 5, 5, 5],
            dtype=float,
            index=_date_index(9),
        )
        result = detect_swings(high, low, order=1)
        # Should find swing highs at 2, 6 and swing low at 4
        kinds = [(sp.index, sp.kind) for sp in result]
        assert (2, "high") in kinds
        assert (4, "low") in kinds
        assert (6, "high") in kinds
        # Must be sorted by index
        indices = [sp.index for sp in result]
        assert indices == sorted(indices)

    def test_empty_when_too_short(self):
        """Very short series produces no swings."""
        high = pd.Series([1.0, 2.0], index=_date_index(2))
        low = pd.Series([0.5, 1.0], index=_date_index(2))
        result = detect_swings(high, low, order=1)
        assert result == []


# ------------------------------------------------------------------
# Real-world–like scenario
# ------------------------------------------------------------------

class TestRealisticScenario:
    """Test with a VCP-like price pattern: declining swing highs, rising lows."""

    def test_vcp_like_pattern(self):
        """Simulate progressively tighter swings mimicking a VCP."""
        # Construct a 30-bar series with 3 contracting waves
        prices_high = [
            # wave 1: peak around bar 5
            100, 102, 105, 108, 112, 115, 112, 108, 105, 102,
            # wave 2: peak around bar 15 (lower high)
            103, 105, 107, 109, 111, 112, 110, 108, 106, 104,
            # wave 3: peak around bar 25 (even lower high)
            105, 106, 107, 108, 109, 110, 109, 108, 107, 106,
        ]
        prices_low = [
            # wave 1: trough around bar 9
            98, 97, 96, 95, 94, 93, 92, 91, 90, 89,
            # wave 2: trough around bar 19 (higher low)
            91, 91, 92, 92, 93, 93, 93, 92, 92, 91,
            # wave 3: trough around bar 29 (even higher low)
            94, 94, 95, 95, 96, 96, 96, 95, 95, 94,
        ]
        idx = _date_index(30)
        high = pd.Series(prices_high, dtype=float, index=idx)
        low = pd.Series(prices_low, dtype=float, index=idx)

        swings = detect_swings(high, low, order=2)

        # Extract swing highs and lows separately
        sh = [sp for sp in swings if sp.kind == "high"]
        sl = [sp for sp in swings if sp.kind == "low"]

        # Should detect at least 2 swing highs (contracting peaks)
        assert len(sh) >= 2, f"Expected ≥2 swing highs, got {len(sh)}: {sh}"
        # Swing highs should be declining (VCP signature)
        for i in range(1, len(sh)):
            assert sh[i].price <= sh[i - 1].price, (
                f"Swing high at bar {sh[i].index} ({sh[i].price}) "
                f"should be ≤ swing high at bar {sh[i - 1].index} ({sh[i - 1].price})"
            )

        # Should detect at least 1 swing low
        assert len(sl) >= 1, f"Expected ≥1 swing lows, got {len(sl)}"


# ------------------------------------------------------------------
# Series helpers
# ------------------------------------------------------------------

class TestSwingSeries:
    """Tests for swing_highs_series / swing_lows_series."""

    def test_highs_series_nan_and_values(self):
        """swing_highs_series returns NaN everywhere except swing highs."""
        high = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0], index=_date_index(5))
        result = swing_highs_series(high, order=1)
        assert len(result) == 5
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 5.0
        assert pd.isna(result.iloc[3])
        assert pd.isna(result.iloc[4])

    def test_lows_series_nan_and_values(self):
        """swing_lows_series returns NaN everywhere except swing lows."""
        low = pd.Series([5.0, 2.0, 1.0, 2.0, 5.0], index=_date_index(5))
        result = swing_lows_series(low, order=1)
        assert len(result) == 5
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 1.0
        assert pd.isna(result.iloc[3])
        assert pd.isna(result.iloc[4])

    def test_series_preserves_index(self):
        """Returned series should share the original index."""
        idx = _date_index(5)
        high = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0], index=idx)
        result = swing_highs_series(high, order=1)
        assert list(result.index) == list(idx)
