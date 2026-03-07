"""Tests for contraction detection logic."""

from __future__ import annotations

import pandas as pd
import pytest

from tayfin_screener_jobs.vcp.contraction_detection import (
    Contraction,
    ContractionSequence,
    detect_contractions,
    extract_contractions,
    find_contraction_sequence,
)
from tayfin_screener_jobs.vcp.swing_detection import SwingPoint


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _date_index(n: int, start: str = "2025-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _sp(index: int, price: float, kind: str = "high") -> SwingPoint:
    """Shorthand to create a SwingPoint."""
    return SwingPoint(index=index, date=f"2025-01-{index+1:02d}", price=price, kind=kind)


# ------------------------------------------------------------------
# extract_contractions
# ------------------------------------------------------------------

class TestExtractContractions:
    """Tests for extract_contractions."""

    def test_declining_highs_form_contraction(self):
        """Two swing highs where the second is lower → one contraction."""
        highs = [_sp(5, 100.0), _sp(15, 95.0)]
        lows = [_sp(10, 85.0, "low")]
        result = extract_contractions(highs, lows)

        assert len(result) == 1
        c = result[0]
        assert c.high_start.price == 100.0
        assert c.high_end.price == 95.0
        assert c.low_between is not None
        assert c.low_between.price == 85.0
        # depth = (100 - 85) / 100 = 0.15
        assert abs(c.depth - 0.15) < 1e-9
        # high_decline = (100 - 95) / 100 = 0.05
        assert abs(c.high_decline - 0.05) < 1e-9

    def test_rising_high_filtered_out(self):
        """Second high significantly above first → no contraction."""
        highs = [_sp(5, 100.0), _sp(15, 110.0)]
        lows = [_sp(10, 90.0, "low")]
        result = extract_contractions(highs, lows, max_high_rise=0.02)
        assert len(result) == 0

    def test_near_equal_highs_within_tolerance(self):
        """Second high slightly above first but within 2% tolerance."""
        highs = [_sp(5, 100.0), _sp(15, 101.5)]
        lows = [_sp(10, 90.0, "low")]
        result = extract_contractions(highs, lows, max_high_rise=0.02)
        assert len(result) == 1

    def test_no_low_between_gives_zero_depth(self):
        """No swing low between the highs → depth = 0."""
        highs = [_sp(5, 100.0), _sp(10, 95.0)]
        lows = []  # no lows at all
        result = extract_contractions(highs, lows)
        assert len(result) == 1
        assert result[0].depth == 0.0
        assert result[0].low_between is None

    def test_multiple_lows_picks_deepest(self):
        """When multiple swing lows exist between highs, pick the deepest."""
        highs = [_sp(5, 100.0), _sp(25, 95.0)]
        lows = [
            _sp(10, 90.0, "low"),
            _sp(15, 85.0, "low"),  # deepest
            _sp(20, 88.0, "low"),
        ]
        result = extract_contractions(highs, lows)
        assert len(result) == 1
        assert result[0].low_between is not None
        assert result[0].low_between.price == 85.0

    def test_three_highs_two_contractions(self):
        """Three declining highs produce two contraction pairs."""
        highs = [_sp(5, 100.0), _sp(15, 95.0), _sp(25, 91.0)]
        lows = [_sp(10, 85.0, "low"), _sp(20, 88.0, "low")]
        result = extract_contractions(highs, lows)
        assert len(result) == 2

    def test_empty_highs(self):
        result = extract_contractions([], [])
        assert result == []

    def test_single_high(self):
        result = extract_contractions([_sp(5, 100.0)], [])
        assert result == []

    def test_low_outside_range_ignored(self):
        """Swing lows outside the range between two highs are ignored."""
        highs = [_sp(10, 100.0), _sp(20, 95.0)]
        lows = [_sp(5, 80.0, "low"), _sp(25, 82.0, "low")]  # both outside
        result = extract_contractions(highs, lows)
        assert len(result) == 1
        assert result[0].low_between is None


# ------------------------------------------------------------------
# find_contraction_sequence
# ------------------------------------------------------------------

class TestFindContractionSequence:
    """Tests for find_contraction_sequence."""

    def _make_contraction(
        self,
        high_start_idx: int,
        high_start_price: float,
        high_end_idx: int,
        high_end_price: float,
        low_idx: int,
        low_price: float,
    ) -> Contraction:
        sh1 = _sp(high_start_idx, high_start_price)
        sh2 = _sp(high_end_idx, high_end_price)
        sl = _sp(low_idx, low_price, "low")
        depth = (high_start_price - low_price) / high_start_price
        high_decline = (high_start_price - high_end_price) / high_start_price
        return Contraction(
            high_start=sh1,
            high_end=sh2,
            low_between=sl,
            depth=depth,
            high_decline=high_decline,
        )

    def test_tightening_sequence_found(self):
        """3 contiguous contractions with decreasing depth → sequence of 3."""
        c1 = self._make_contraction(5, 100, 15, 95, 10, 80)   # depth=0.20
        c2 = self._make_contraction(15, 95, 25, 92, 20, 85)   # depth≈0.105
        c3 = self._make_contraction(25, 92, 35, 90, 30, 88)   # depth≈0.043
        seq = find_contraction_sequence([c1, c2, c3], min_contractions=2)
        assert seq.count == 3
        assert seq.is_tightening

    def test_non_tightening_rejected(self):
        """Non-tightening sequence → empty when require_tightening=True."""
        c1 = self._make_contraction(5, 100, 15, 95, 10, 85)   # depth=0.15
        c2 = self._make_contraction(15, 95, 25, 92, 20, 75)   # depth≈0.21 (deeper!)
        seq = find_contraction_sequence([c1, c2], min_contractions=2, require_tightening=True)
        assert seq.count == 0

    def test_non_tightening_accepted_when_not_required(self):
        """Non-tightening allowed when require_tightening=False."""
        c1 = self._make_contraction(5, 100, 15, 95, 10, 85)
        c2 = self._make_contraction(15, 95, 25, 92, 20, 75)
        seq = find_contraction_sequence([c1, c2], min_contractions=2, require_tightening=False)
        assert seq.count == 2

    def test_non_contiguous_breaks_sequence(self):
        """Gap in contiguity (end of c1 ≠ start of c2) starts a new run."""
        c1 = self._make_contraction(5, 100, 15, 95, 10, 85)
        # c2 starts at index 20, not 15 → not contiguous
        c2 = self._make_contraction(20, 93, 30, 90, 25, 88)
        seq = find_contraction_sequence([c1, c2], min_contractions=2)
        assert seq.count == 0  # each run has only 1

    def test_picks_longest_run(self):
        """When there are two valid runs, return the longer one."""
        # Run 1: 2 contractions (indices 5→15→25)
        c1 = self._make_contraction(5, 100, 15, 95, 10, 80)   # depth=0.20
        c2 = self._make_contraction(15, 95, 25, 92, 20, 85)   # depth≈0.105

        # Gap
        c3 = self._make_contraction(30, 110, 40, 108, 35, 98)  # depth≈0.109

        # Run 2: 3 contractions (indices 40→50→60→70)
        c4 = self._make_contraction(40, 108, 50, 105, 45, 96)  # depth≈0.111
        c5 = self._make_contraction(50, 105, 60, 103, 55, 99)  # depth≈0.057
        c6 = self._make_contraction(60, 103, 70, 101, 65, 100) # depth≈0.029

        seq = find_contraction_sequence([c1, c2, c3, c4, c5, c6], min_contractions=2)
        assert seq.count == 3  # run 2 is longer
        assert seq.contractions[0].high_start.index == 40

    def test_below_min_returns_empty(self):
        """Single contraction with min_contractions=2 → empty."""
        c1 = self._make_contraction(5, 100, 15, 95, 10, 85)
        seq = find_contraction_sequence([c1], min_contractions=2)
        assert seq.count == 0

    def test_empty_input(self):
        seq = find_contraction_sequence([], min_contractions=2)
        assert seq.count == 0


# ------------------------------------------------------------------
# ContractionSequence
# ------------------------------------------------------------------

class TestContractionSequence:
    """Tests for ContractionSequence data class."""

    def test_empty_sequence_properties(self):
        seq = ContractionSequence()
        assert seq.count == 0
        assert seq.depths == []
        assert seq.total_decline == 0.0
        assert seq.is_tightening is False
        d = seq.to_dict()
        assert d["count"] == 0
        assert d["contractions"] == []

    def test_to_dict_serialization(self):
        sh1 = _sp(5, 100.0)
        sh2 = _sp(15, 95.0)
        sl = _sp(10, 85.0, "low")
        c = Contraction(
            high_start=sh1,
            high_end=sh2,
            low_between=sl,
            depth=0.15,
            high_decline=0.05,
        )
        seq = ContractionSequence(contractions=[c])
        d = seq.to_dict()
        assert d["count"] == 1
        assert len(d["contractions"]) == 1
        assert d["contractions"][0]["depth"] == 0.15
        assert d["contractions"][0]["low_price"] == 85.0
        assert d["total_decline"] == 0.05

    def test_total_decline_spans_full_range(self):
        """total_decline = (first_high_start - last_high_end) / first_high_start."""
        sh1, sh2, sh3 = _sp(5, 100.0), _sp(15, 95.0), _sp(25, 90.0)
        sl1, sl2 = _sp(10, 85.0, "low"), _sp(20, 88.0, "low")
        c1 = Contraction(high_start=sh1, high_end=sh2, low_between=sl1, depth=0.15, high_decline=0.05)
        c2 = Contraction(high_start=sh2, high_end=sh3, low_between=sl2, depth=0.074, high_decline=0.053)
        seq = ContractionSequence(contractions=[c1, c2])
        # (100 - 90) / 100 = 0.10
        assert abs(seq.total_decline - 0.10) < 1e-9

    def test_is_tightening_true(self):
        sh1, sh2, sh3 = _sp(5, 100.0), _sp(15, 95.0), _sp(25, 92.0)
        sl1, sl2 = _sp(10, 85.0, "low"), _sp(20, 90.0, "low")
        c1 = Contraction(high_start=sh1, high_end=sh2, low_between=sl1, depth=0.15, high_decline=0.05)
        c2 = Contraction(high_start=sh2, high_end=sh3, low_between=sl2, depth=0.053, high_decline=0.032)
        seq = ContractionSequence(contractions=[c1, c2])
        assert seq.is_tightening is True

    def test_is_tightening_false(self):
        sh1, sh2, sh3 = _sp(5, 100.0), _sp(15, 95.0), _sp(25, 92.0)
        sl1, sl2 = _sp(10, 85.0, "low"), _sp(20, 80.0, "low")
        c1 = Contraction(high_start=sh1, high_end=sh2, low_between=sl1, depth=0.15, high_decline=0.05)
        c2 = Contraction(high_start=sh2, high_end=sh3, low_between=sl2, depth=0.158, high_decline=0.032)
        seq = ContractionSequence(contractions=[c1, c2])
        assert seq.is_tightening is False


# ------------------------------------------------------------------
# detect_contractions (end-to-end pipeline)
# ------------------------------------------------------------------

class TestDetectContractions:
    """Tests for the convenience pipeline."""

    def test_vcp_like_pattern(self):
        """Simulated VCP with 3 contracting waves → valid sequence."""
        # ~50 bars with 3 progressively tighter peaks
        prices_high = (
            # wave 1: peak ~bar 7
            [95, 98, 102, 106, 110, 113, 115, 118, 115, 112, 108, 105]
            # wave 2: peak ~bar 19 (lower high)
            + [106, 108, 110, 112, 113, 114, 115, 116, 114, 112, 110, 108]
            # wave 3: peak ~bar 31 (even lower)
            + [109, 110, 111, 112, 113, 113.5, 114, 114.5, 113, 112, 111, 110]
            # tail
            + [110, 110, 111, 111, 112, 112]
        )
        prices_low = (
            # wave 1: trough ~bar 11
            [90, 91, 92, 93, 94, 95, 96, 95, 94, 93, 90, 89]
            # wave 2: trough ~bar 23 (higher low)
            + [91, 92, 93, 94, 95, 96, 97, 96, 95, 94, 93, 92]
            # wave 3: trough ~bar 35 (even higher low)
            + [95, 96, 97, 98, 99, 100, 101, 100, 99, 98, 97, 96]
            # tail
            + [100, 100, 101, 101, 102, 102]
        )
        n = len(prices_high)
        idx = _date_index(n)
        high = pd.Series(prices_high, dtype=float, index=idx)
        low = pd.Series(prices_low, dtype=float, index=idx)

        seq = detect_contractions(
            high, low,
            swing_order=3,
            min_contractions=2,
            require_tightening=True,
        )

        # Should detect a valid tightening sequence
        assert seq.count >= 2, f"Expected ≥2 contractions, got {seq.count}"
        assert seq.is_tightening
        # Depths should be decreasing
        for i in range(1, len(seq.depths)):
            assert seq.depths[i] < seq.depths[i - 1]

    def test_flat_data_no_contractions(self):
        """Flat price data → no contractions."""
        n = 50
        idx = _date_index(n)
        high = pd.Series([100.0] * n, index=idx)
        low = pd.Series([99.0] * n, index=idx)
        seq = detect_contractions(high, low, swing_order=3, min_contractions=2)
        assert seq.count == 0

    def test_monotonic_up_no_contractions(self):
        """Monotonically rising prices → no swing highs → no contractions."""
        n = 50
        idx = _date_index(n)
        high = pd.Series(range(100, 100 + n), dtype=float, index=idx)
        low = pd.Series(range(99, 99 + n), dtype=float, index=idx)
        seq = detect_contractions(high, low, swing_order=3, min_contractions=2)
        assert seq.count == 0

    def test_short_series_no_crash(self):
        """Very short series doesn't crash, just returns empty."""
        idx = _date_index(5)
        high = pd.Series([100, 105, 103, 102, 101], dtype=float, index=idx)
        low = pd.Series([98, 99, 97, 96, 95], dtype=float, index=idx)
        seq = detect_contractions(high, low, swing_order=2, min_contractions=2)
        assert seq.count == 0

    def test_to_dict_roundtrip(self):
        """Pipeline output → to_dict → verify JSON-serialisable."""
        import json

        prices_high = (
            [95, 100, 105, 110, 115, 120, 115, 110, 105, 100, 95, 90]
            + [93, 96, 100, 104, 108, 112, 108, 104, 100, 96, 93, 90]
            + [92, 94, 97, 100, 103, 105, 103, 100, 97, 94, 92, 90]
        )
        prices_low = (
            [88, 90, 92, 94, 96, 98, 96, 94, 92, 88, 85, 83]
            + [85, 87, 89, 91, 93, 95, 93, 91, 89, 87, 85, 84]
            + [87, 88, 90, 92, 94, 96, 94, 92, 90, 88, 87, 86]
        )
        n = len(prices_high)
        idx = _date_index(n)
        high = pd.Series(prices_high, dtype=float, index=idx)
        low = pd.Series(prices_low, dtype=float, index=idx)

        seq = detect_contractions(high, low, swing_order=2, min_contractions=1,
                                  require_tightening=False)
        d = seq.to_dict()
        # Must be JSON-serialisable
        serialised = json.dumps(d)
        assert isinstance(serialised, str)
        assert "count" in d
        assert "depths" in d
