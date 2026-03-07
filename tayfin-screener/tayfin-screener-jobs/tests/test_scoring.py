"""Tests for tayfin_screener_jobs.vcp.scoring."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.vcp.scoring import (
    MAX_CONTRACTION_SCORE,
    MAX_TREND_SCORE,
    MAX_VOLUME_SCORE,
    PATTERN_SCORE_THRESHOLD,
    ScoringResult,
    _determine_confidence,
    compute_vcp_score,
    score_contractions,
    score_trend,
    score_volume,
)


# ===================================================================
# Helpers — reusable feature dicts
# ===================================================================

def _strong_contraction() -> dict:
    """3 tightening contractions with ideal total decline."""
    return {"count": 3, "is_tightening": True, "total_decline": 0.20}


def _weak_contraction() -> dict:
    """1 contraction, no tightening, shallow decline."""
    return {"count": 1, "is_tightening": False, "total_decline": 0.03}


def _no_contraction() -> dict:
    return {"count": 0, "is_tightening": False, "total_decline": 0.0}


def _strong_trend() -> dict:
    return {
        "ma_alignment": True,
        "near_52w_high": True,
        "atr_trend": -0.15,
        "sma_50_slope": 0.08,
    }


def _weak_trend() -> dict:
    return {
        "ma_alignment": False,
        "near_52w_high": False,
        "atr_trend": 0.05,
        "sma_50_slope": -0.02,
    }


def _strong_volume() -> dict:
    return {
        "volume_dryup": True,
        "volume_trend": -0.20,
        "volume_contraction_pct": 0.60,
    }


def _weak_volume() -> dict:
    return {
        "volume_dryup": False,
        "volume_trend": 0.10,
        "volume_contraction_pct": 0.05,
    }


# ===================================================================
# TestScoreContractions
# ===================================================================

class TestScoreContractions:
    """Tests for :func:`score_contractions`."""

    # -- count tiers --

    def test_zero_contractions_scores_zero(self):
        assert score_contractions({"count": 0}) == 0.0

    def test_one_contraction_scores_3(self):
        assert score_contractions({"count": 1, "is_tightening": False, "total_decline": 0.0}) == 3.0

    def test_two_contractions_scores_8_base(self):
        result = score_contractions({"count": 2, "is_tightening": False, "total_decline": 0.0})
        assert result == 8.0

    def test_three_contractions_scores_12_base(self):
        result = score_contractions({"count": 3, "is_tightening": False, "total_decline": 0.0})
        assert result == 12.0

    def test_four_plus_contractions_scores_15_base(self):
        result = score_contractions({"count": 5, "is_tightening": False, "total_decline": 0.0})
        assert result == 15.0

    # -- tightening bonus --

    def test_tightening_with_two_contractions_adds_10(self):
        result = score_contractions({"count": 2, "is_tightening": True, "total_decline": 0.0})
        assert result == 18.0  # 8 + 10

    def test_tightening_with_one_contraction_no_bonus(self):
        result = score_contractions({"count": 1, "is_tightening": True, "total_decline": 0.0})
        assert result == 3.0  # no bonus when count < 2

    def test_tightening_false_no_bonus(self):
        result = score_contractions({"count": 3, "is_tightening": False, "total_decline": 0.0})
        assert result == 12.0

    # -- total decline tiers --

    def test_ideal_decline_range_adds_10(self):
        result = score_contractions({"count": 0, "is_tightening": False, "total_decline": 0.20})
        assert result == 10.0

    def test_lower_boundary_ideal_decline(self):
        result = score_contractions({"count": 0, "total_decline": 0.10})
        assert result == 10.0

    def test_upper_boundary_ideal_decline(self):
        result = score_contractions({"count": 0, "total_decline": 0.35})
        assert result == 10.0

    def test_near_ideal_low_decline_adds_5(self):
        result = score_contractions({"count": 0, "total_decline": 0.07})
        assert result == 5.0

    def test_near_ideal_high_decline_adds_5(self):
        result = score_contractions({"count": 0, "total_decline": 0.45})
        assert result == 5.0

    def test_decline_above_050_no_points(self):
        result = score_contractions({"count": 0, "total_decline": 0.55})
        assert result == 0.0

    def test_decline_below_005_no_points(self):
        result = score_contractions({"count": 0, "total_decline": 0.02})
        assert result == 0.0

    # -- cap at max --

    def test_score_capped_at_max(self):
        # 4 contractions (15) + tightening (10) + ideal decline (10) = 35 = max
        result = score_contractions({"count": 4, "is_tightening": True, "total_decline": 0.20})
        assert result == MAX_CONTRACTION_SCORE

    # -- missing keys --

    def test_empty_dict_scores_zero(self):
        assert score_contractions({}) == 0.0


# ===================================================================
# TestScoreTrend
# ===================================================================

class TestScoreTrend:
    """Tests for :func:`score_trend`."""

    def test_ma_alignment_adds_15(self):
        result = score_trend({"ma_alignment": True})
        assert result == 15.0

    def test_no_ma_alignment(self):
        result = score_trend({"ma_alignment": False})
        assert result == 0.0

    def test_near_52w_high_adds_10(self):
        result = score_trend({"near_52w_high": True})
        assert result == 10.0

    def test_atr_trend_strongly_negative_adds_5(self):
        result = score_trend({"atr_trend": -0.15})
        assert result == 5.0

    def test_atr_trend_slightly_negative_adds_3(self):
        result = score_trend({"atr_trend": -0.05})
        assert result == 3.0

    def test_atr_trend_zero_adds_nothing(self):
        result = score_trend({"atr_trend": 0.0})
        assert result == 0.0

    def test_atr_trend_positive_adds_nothing(self):
        result = score_trend({"atr_trend": 0.10})
        assert result == 0.0

    def test_sma_slope_strongly_positive_adds_5(self):
        result = score_trend({"sma_50_slope": 0.08})
        assert result == 5.0

    def test_sma_slope_slightly_positive_adds_3(self):
        result = score_trend({"sma_50_slope": 0.02})
        assert result == 3.0

    def test_sma_slope_zero_adds_nothing(self):
        result = score_trend({"sma_50_slope": 0.0})
        assert result == 0.0

    def test_sma_slope_negative_adds_nothing(self):
        result = score_trend({"sma_50_slope": -0.03})
        assert result == 0.0

    def test_full_score(self):
        features = _strong_trend()
        result = score_trend(features)
        assert result == MAX_TREND_SCORE  # 15 + 10 + 5 + 5

    def test_empty_dict_scores_zero(self):
        assert score_trend({}) == 0.0


# ===================================================================
# TestScoreVolume
# ===================================================================

class TestScoreVolume:
    """Tests for :func:`score_volume`."""

    def test_volume_dryup_adds_15(self):
        result = score_volume({"volume_dryup": True})
        assert result == 15.0

    def test_no_volume_dryup(self):
        result = score_volume({"volume_dryup": False})
        assert result == 0.0

    def test_volume_trend_strongly_negative_adds_5(self):
        result = score_volume({"volume_trend": -0.20})
        assert result == 5.0

    def test_volume_trend_slightly_negative_adds_3(self):
        result = score_volume({"volume_trend": -0.05})
        assert result == 3.0

    def test_volume_trend_zero_adds_nothing(self):
        result = score_volume({"volume_trend": 0.0})
        assert result == 0.0

    def test_volume_trend_positive_adds_nothing(self):
        result = score_volume({"volume_trend": 0.15})
        assert result == 0.0

    def test_contraction_pct_high_adds_10(self):
        result = score_volume({"volume_contraction_pct": 0.55})
        assert result == 10.0

    def test_contraction_pct_medium_adds_6(self):
        result = score_volume({"volume_contraction_pct": 0.35})
        assert result == 6.0

    def test_contraction_pct_low_adds_3(self):
        result = score_volume({"volume_contraction_pct": 0.20})
        assert result == 3.0

    def test_contraction_pct_below_threshold_adds_nothing(self):
        result = score_volume({"volume_contraction_pct": 0.10})
        assert result == 0.0

    def test_contraction_pct_boundary_050(self):
        result = score_volume({"volume_contraction_pct": 0.50})
        assert result == 10.0

    def test_contraction_pct_boundary_030(self):
        result = score_volume({"volume_contraction_pct": 0.30})
        assert result == 6.0

    def test_contraction_pct_boundary_015(self):
        result = score_volume({"volume_contraction_pct": 0.15})
        assert result == 3.0

    def test_full_score(self):
        features = _strong_volume()
        result = score_volume(features)
        assert result == MAX_VOLUME_SCORE  # 15 + 5 + 10

    def test_empty_dict_scores_zero(self):
        assert score_volume({}) == 0.0


# ===================================================================
# TestDetermineConfidence
# ===================================================================

class TestDetermineConfidence:
    """Tests for :func:`_determine_confidence`."""

    def test_high_confidence_all_criteria_met(self):
        result = _determine_confidence(
            75.0, _strong_contraction(), _strong_trend(), _strong_volume(),
        )
        assert result == "high"

    def test_high_score_but_no_tightening_gives_medium(self):
        contraction = {"count": 3, "is_tightening": False, "total_decline": 0.20}
        result = _determine_confidence(75.0, contraction, _strong_trend(), _strong_volume())
        assert result == "medium"

    def test_high_score_but_no_ma_alignment_gives_medium(self):
        trend = {**_strong_trend(), "ma_alignment": False}
        result = _determine_confidence(75.0, _strong_contraction(), trend, _strong_volume())
        assert result == "medium"

    def test_high_score_but_not_near_52w_gives_medium(self):
        trend = {**_strong_trend(), "near_52w_high": False}
        result = _determine_confidence(75.0, _strong_contraction(), trend, _strong_volume())
        assert result == "medium"

    def test_high_score_but_only_one_contraction_gives_medium(self):
        contraction = {"count": 1, "is_tightening": True, "total_decline": 0.20}
        result = _determine_confidence(75.0, contraction, _strong_trend(), _strong_volume())
        assert result == "medium"

    def test_score_at_medium_threshold(self):
        result = _determine_confidence(50.0, _weak_contraction(), _weak_trend(), _weak_volume())
        assert result == "medium"

    def test_score_below_medium_threshold_is_low(self):
        result = _determine_confidence(45.0, _weak_contraction(), _weak_trend(), _weak_volume())
        assert result == "low"

    def test_zero_score_is_low(self):
        result = _determine_confidence(0.0, _no_contraction(), _weak_trend(), _weak_volume())
        assert result == "low"

    def test_score_exactly_at_high_threshold_with_criteria(self):
        result = _determine_confidence(
            70.0, _strong_contraction(), _strong_trend(), _strong_volume(),
        )
        assert result == "high"


# ===================================================================
# TestScoringResult
# ===================================================================

class TestScoringResult:
    """Tests for the :class:`ScoringResult` dataclass."""

    def test_frozen(self):
        r = ScoringResult(score=50.0, confidence="medium", pattern_detected=True, breakdown={})
        with pytest.raises(AttributeError):
            r.score = 99  # type: ignore[misc]

    def test_fields(self):
        r = ScoringResult(
            score=72.0,
            confidence="high",
            pattern_detected=True,
            breakdown={"contraction": 32.0, "trend": 25.0, "volume": 15.0},
        )
        assert r.score == 72.0
        assert r.confidence == "high"
        assert r.pattern_detected is True
        assert r.breakdown["contraction"] == 32.0


# ===================================================================
# TestComputeVcpScore — integration / composite
# ===================================================================

class TestComputeVcpScore:
    """Tests for the top-level :func:`compute_vcp_score`."""

    def test_perfect_vcp_scores_100(self):
        result = compute_vcp_score(
            contraction_features={"count": 4, "is_tightening": True, "total_decline": 0.20},
            volatility_features=_strong_trend(),
            volume_features=_strong_volume(),
        )
        assert result.score == 100.0
        assert result.confidence == "high"
        assert result.pattern_detected is True
        assert result.breakdown["contraction"] == MAX_CONTRACTION_SCORE
        assert result.breakdown["trend"] == MAX_TREND_SCORE
        assert result.breakdown["volume"] == MAX_VOLUME_SCORE

    def test_no_features_scores_zero(self):
        result = compute_vcp_score(
            contraction_features={},
            volatility_features={},
            volume_features={},
        )
        assert result.score == 0.0
        assert result.confidence == "low"
        assert result.pattern_detected is False

    def test_pattern_detected_requires_min_2_contractions(self):
        """Score above threshold but only 1 contraction → no pattern."""
        result = compute_vcp_score(
            contraction_features={"count": 1, "is_tightening": False, "total_decline": 0.20},
            volatility_features=_strong_trend(),
            volume_features=_strong_volume(),
        )
        assert result.score >= PATTERN_SCORE_THRESHOLD
        assert result.pattern_detected is False

    def test_pattern_detected_requires_min_score(self):
        """2+ contractions but very low score → no pattern."""
        result = compute_vcp_score(
            contraction_features={"count": 2, "is_tightening": False, "total_decline": 0.0},
            volatility_features=_weak_trend(),
            volume_features=_weak_volume(),
        )
        assert result.score < PATTERN_SCORE_THRESHOLD
        assert result.pattern_detected is False

    def test_moderate_features_medium_confidence(self):
        result = compute_vcp_score(
            contraction_features={"count": 2, "is_tightening": True, "total_decline": 0.15},
            volatility_features={
                "ma_alignment": True,
                "near_52w_high": False,
                "atr_trend": -0.05,
                "sma_50_slope": 0.02,
            },
            volume_features={
                "volume_dryup": False,
                "volume_trend": -0.05,
                "volume_contraction_pct": 0.20,
            },
        )
        # 8+10+10=28 contraction, 15+0+3+3=21 trend, 0+3+3=6 vol → 55
        assert result.score == 55.0
        assert result.confidence == "medium"
        assert result.pattern_detected is True

    def test_breakdown_sums_to_score(self):
        result = compute_vcp_score(
            contraction_features=_strong_contraction(),
            volatility_features=_strong_trend(),
            volume_features=_strong_volume(),
        )
        assert result.score == pytest.approx(
            result.breakdown["contraction"]
            + result.breakdown["trend"]
            + result.breakdown["volume"],
        )

    def test_score_never_exceeds_100(self):
        """Even with maximum inputs, score caps at 100."""
        result = compute_vcp_score(
            contraction_features={"count": 10, "is_tightening": True, "total_decline": 0.25},
            volatility_features=_strong_trend(),
            volume_features=_strong_volume(),
        )
        assert result.score <= 100.0

    def test_returns_scoring_result_type(self):
        result = compute_vcp_score(
            contraction_features=_no_contraction(),
            volatility_features={},
            volume_features={},
        )
        assert isinstance(result, ScoringResult)

    def test_strong_contractions_weak_else(self):
        result = compute_vcp_score(
            contraction_features=_strong_contraction(),
            volatility_features=_weak_trend(),
            volume_features=_weak_volume(),
        )
        assert result.breakdown["contraction"] == 32.0  # 12+10+10
        assert result.breakdown["trend"] == 0.0
        assert result.breakdown["volume"] == 0.0
        assert result.score == 32.0
        assert result.pattern_detected is False

    def test_no_contractions_strong_else(self):
        result = compute_vcp_score(
            contraction_features=_no_contraction(),
            volatility_features=_strong_trend(),
            volume_features=_strong_volume(),
        )
        assert result.breakdown["contraction"] == 0.0
        assert result.pattern_detected is False  # 0 contractions
