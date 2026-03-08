"""Smoke tests for the MCSA criteria and evaluator.

Pure-logic tests — no DB, no network.
"""

from __future__ import annotations

from datetime import date

import pytest

from tayfin_screener_jobs.mcsa.criteria import (
    criterion_1,
    criterion_2,
    criterion_3,
    criterion_4,
    criterion_5,
    criterion_6,
    criterion_7,
    criterion_8,
)
from tayfin_screener_jobs.mcsa.evaluate import McsaResult, evaluate_mcsa


# ===================================================================
# Criterion unit tests
# ===================================================================


class TestCriterion1:
    """C1: close > SMA-200 AND SMA-200 slope > 0."""

    def test_pass(self):
        assert criterion_1(close=110, sma_200=100, sma_200_slope=0.01) is True

    def test_fail_below_sma_200(self):
        assert criterion_1(close=90, sma_200=100, sma_200_slope=0.01) is False

    def test_fail_negative_slope(self):
        assert criterion_1(close=110, sma_200=100, sma_200_slope=-0.01) is False


class TestCriterion2:
    """C2: SMA-150 > SMA-200."""

    def test_pass(self):
        assert criterion_2(sma_150=110, sma_200=100) is True

    def test_fail(self):
        assert criterion_2(sma_150=90, sma_200=100) is False

    def test_equal(self):
        assert criterion_2(sma_150=100, sma_200=100) is False


class TestCriterion3:
    """C3: SMA-50 > SMA-150 AND SMA-50 > SMA-200."""

    def test_pass(self):
        assert criterion_3(sma_50=120, sma_150=110, sma_200=100) is True

    def test_fail_below_150(self):
        assert criterion_3(sma_50=105, sma_150=110, sma_200=100) is False

    def test_fail_below_200(self):
        assert criterion_3(sma_50=105, sma_150=100, sma_200=110) is False


class TestCriterion4:
    """C4: close > SMA-50."""

    def test_pass(self):
        assert criterion_4(close=110, sma_50=100) is True

    def test_fail(self):
        assert criterion_4(close=90, sma_50=100) is False


class TestCriterion5:
    """C5: close >= 1.25 * rolling_low_252."""

    def test_pass(self):
        assert criterion_5(close=125, rolling_low_252=100) is True

    def test_pass_above(self):
        assert criterion_5(close=150, rolling_low_252=100) is True

    def test_fail(self):
        assert criterion_5(close=120, rolling_low_252=100) is False


class TestCriterion6:
    """C6: close >= 0.75 * rolling_high_252."""

    def test_pass(self):
        assert criterion_6(close=80, rolling_high_252=100) is True

    def test_fail(self):
        assert criterion_6(close=70, rolling_high_252=100) is False

    def test_boundary(self):
        assert criterion_6(close=75, rolling_high_252=100) is True


class TestCriterion7:
    """C7: RS rank > 70 (top 30th percentile)."""

    def test_pass(self):
        assert criterion_7(rs_rank=80) is True

    def test_fail(self):
        assert criterion_7(rs_rank=50) is False

    def test_boundary(self):
        assert criterion_7(rs_rank=70) is False


class TestCriterion8:
    """C8: close > SMA-50 for at least 5 of last 10 days."""

    def test_pass_all_above(self):
        closes = [110] * 10
        sma_50 = [100] * 10
        assert criterion_8(recent_closes=closes, recent_sma_50=sma_50) is True

    def test_pass_exactly_5(self):
        closes = [110, 110, 110, 110, 110, 90, 90, 90, 90, 90]
        sma_50 = [100] * 10
        assert criterion_8(recent_closes=closes, recent_sma_50=sma_50) is True

    def test_fail_only_4(self):
        closes = [110, 110, 110, 110, 90, 90, 90, 90, 90, 90]
        sma_50 = [100] * 10
        assert criterion_8(recent_closes=closes, recent_sma_50=sma_50) is False

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            criterion_8(recent_closes=[110] * 5, recent_sma_50=[100] * 3)


# ===================================================================
# Evaluator integration test
# ===================================================================


class TestEvaluateMcsa:
    """Smoke test for :func:`evaluate_mcsa`."""

    def _perfect_stock(self) -> dict:
        """Return kwargs for a stock that passes all 8 criteria."""
        return {
            "ticker": "AAPL",
            "as_of_date": date(2026, 3, 8),
            "close": 200.0,
            "sma_50": 190.0,
            "sma_150": 180.0,
            "sma_200": 170.0,
            "sma_200_slope": 0.05,
            "rolling_high_252": 210.0,
            "rolling_low_252": 140.0,  # 200 >= 1.25*140=175 ✓
            "rs_rank": 85.0,
            "recent_closes": [200.0] * 10,
            "recent_sma_50": [190.0] * 10,
        }

    def test_all_pass(self):
        result = evaluate_mcsa(**self._perfect_stock())
        assert isinstance(result, McsaResult)
        assert result.mcsa_pass is True
        assert result.criteria_count_pass == 8
        assert result.ticker == "AAPL"

    def test_failing_stock(self):
        kwargs = self._perfect_stock()
        kwargs["close"] = 100.0  # below SMA-200 → C1 fail, below SMA-50 → C4 fail
        kwargs["rs_rank"] = 30.0  # C7 fails
        kwargs["recent_closes"] = [100.0] * 10
        result = evaluate_mcsa(**kwargs)
        assert result.mcsa_pass is False
        assert result.criteria_count_pass < 8

    def test_criteria_json_has_all_8_keys(self):
        result = evaluate_mcsa(**self._perfect_stock())
        cj = result.criteria_json
        assert len(cj) == 8
        # All keys start with "c" and contain criterion info
        for key in cj:
            assert key.startswith("c")

    def test_as_of_date_preserved(self):
        result = evaluate_mcsa(**self._perfect_stock())
        assert result.as_of_date == date(2026, 3, 8)

    def test_rs_rank_preserved(self):
        result = evaluate_mcsa(**self._perfect_stock())
        assert result.rs_rank == 85.0
