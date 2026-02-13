"""Unit tests for pure indicator computation functions.

No DB, no network — only pandas math.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tayfin_indicator_jobs.indicator.compute import (
    compute_atr,
    compute_rolling_high,
    compute_sma,
    compute_true_range,
    compute_vol_sma,
)


# ── helpers ──────────────────────────────────────────────────────────


def _close_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def _ohlcv_series(rows: list[tuple[float, float, float]]):
    """Return (high, low, close) Series from (h, l, c) tuples."""
    high = pd.Series([r[0] for r in rows], dtype=float)
    low = pd.Series([r[1] for r in rows], dtype=float)
    close = pd.Series([r[2] for r in rows], dtype=float)
    return high, low, close


# ── SMA ──────────────────────────────────────────────────────────────


class TestComputeSma:
    def test_basic_sma(self):
        close = _close_series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_sma(close, window=3)
        assert len(result) == 5
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
        assert result.iloc[3] == pytest.approx(3.0)  # (2+3+4)/3
        assert result.iloc[4] == pytest.approx(4.0)  # (3+4+5)/3

    def test_sma_output_length(self):
        close = _close_series([10.0] * 20)
        result = compute_sma(close, window=5)
        assert len(result) == 20
        # First 4 are NaN, rest are 10.0
        assert result.isna().sum() == 4
        assert result.dropna().unique().tolist() == [10.0]

    def test_sma_window_1_equals_close(self):
        close = _close_series([7.0, 8.0, 9.0])
        result = compute_sma(close, window=1)
        pd.testing.assert_series_equal(result, close)

    def test_sma_all_nan_when_too_few(self):
        close = _close_series([1.0, 2.0])
        result = compute_sma(close, window=5)
        assert result.isna().all()


# ── True Range ───────────────────────────────────────────────────────


class TestComputeTrueRange:
    def test_first_row_uses_high_minus_low(self):
        high, low, close = _ohlcv_series([(12.0, 8.0, 10.0)])
        tr = compute_true_range(high, low, close)
        assert tr.iloc[0] == pytest.approx(4.0)  # 12 - 8

    def test_tr_formula(self):
        # Day 0: H=12, L=8, C=10  → TR = 4.0 (first row)
        # Day 1: H=15, L=9, C=14  → prev_close=10
        #   H-L=6, |H-prevC|=5, |L-prevC|=1  → max=6
        high, low, close = _ohlcv_series(
            [(12.0, 8.0, 10.0), (15.0, 9.0, 14.0)]
        )
        tr = compute_true_range(high, low, close)
        assert tr.iloc[0] == pytest.approx(4.0)
        assert tr.iloc[1] == pytest.approx(6.0)

    def test_tr_gap_up(self):
        # Day 0: H=10, L=8, C=9
        # Day 1: H=20, L=18, C=19 → prev_close=9
        #   H-L=2, |H-prevC|=11, |L-prevC|=9  → max=11
        high, low, close = _ohlcv_series(
            [(10.0, 8.0, 9.0), (20.0, 18.0, 19.0)]
        )
        tr = compute_true_range(high, low, close)
        assert tr.iloc[1] == pytest.approx(11.0)

    def test_tr_gap_down(self):
        # Day 0: H=20, L=18, C=19
        # Day 1: H=12, L=10, C=11 → prev_close=19
        #   H-L=2, |H-prevC|=7, |L-prevC|=9  → max=9
        high, low, close = _ohlcv_series(
            [(20.0, 18.0, 19.0), (12.0, 10.0, 11.0)]
        )
        tr = compute_true_range(high, low, close)
        assert tr.iloc[1] == pytest.approx(9.0)


# ── ATR ──────────────────────────────────────────────────────────────


class TestComputeAtr:
    def test_atr_window_equals_sma_of_tr(self):
        high, low, close = _ohlcv_series(
            [
                (12.0, 8.0, 10.0),
                (15.0, 9.0, 14.0),
                (16.0, 11.0, 13.0),
                (14.0, 10.0, 12.0),
            ]
        )
        atr = compute_atr(high, low, close, window=2)
        tr = compute_true_range(high, low, close)
        expected_sma = tr.rolling(2).mean()
        pd.testing.assert_series_equal(atr, expected_sma)

    def test_atr_output_length(self):
        rows = [(100.0 + i, 95.0 + i, 98.0 + i) for i in range(30)]
        high, low, close = _ohlcv_series(rows)
        atr = compute_atr(high, low, close, window=14)
        assert len(atr) == 30
        # First 13 values should be NaN (window-1 from TR SMA)
        assert atr.isna().sum() == 13


# ── Volume SMA ───────────────────────────────────────────────────────


class TestComputeVolSma:
    def test_vol_sma_basic(self):
        vol = pd.Series([100, 200, 300, 400, 500], dtype=float)
        result = compute_vol_sma(vol, window=3)
        assert result.iloc[2] == pytest.approx(200.0)  # (100+200+300)/3
        assert result.iloc[4] == pytest.approx(400.0)  # (300+400+500)/3

    def test_vol_sma_output_length(self):
        vol = pd.Series([1_000_000] * 50, dtype=float)
        result = compute_vol_sma(vol, window=10)
        assert len(result) == 50
        assert result.isna().sum() == 9


# ── Rolling High ─────────────────────────────────────────────────────


class TestComputeRollingHigh:
    def test_rolling_high_basic(self):
        close = _close_series([5.0, 3.0, 8.0, 2.0, 7.0])
        result = compute_rolling_high(close, window=3)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == pytest.approx(8.0)  # max(5,3,8)
        assert result.iloc[3] == pytest.approx(8.0)  # max(3,8,2)
        assert result.iloc[4] == pytest.approx(8.0)  # max(8,2,7)

    def test_monotone_increasing(self):
        close = _close_series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute_rolling_high(close, window=3)
        assert result.iloc[2] == pytest.approx(3.0)
        assert result.iloc[3] == pytest.approx(4.0)
        assert result.iloc[4] == pytest.approx(5.0)

    def test_monotone_decreasing(self):
        close = _close_series([5.0, 4.0, 3.0, 2.0, 1.0])
        result = compute_rolling_high(close, window=3)
        # Rolling high tracks the first value in the window
        assert result.iloc[2] == pytest.approx(5.0)
        assert result.iloc[3] == pytest.approx(4.0)
        assert result.iloc[4] == pytest.approx(3.0)
