"""Tests for tayfin_screener_jobs.mcsa.scoring."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.mcsa.config import McsaConfig, build_mcsa_config
from tayfin_screener_jobs.mcsa.scoring import (
    FundamentalsInput,
    McsaDataError,
    McsaInput,
    McsaResult,
    TrendInput,
    VcpInput,
    VolumeInput,
    compute_mcsa_score,
)


# ===================================================================
# Helpers — reusable config + inputs
# ===================================================================

def _default_cfg() -> McsaConfig:
    """Return the default McsaConfig (ADR-01 defaults)."""
    return build_mcsa_config(None)


def _strong_trend() -> TrendInput:
    """Trend where all checks pass (price above SMAs, near 52w high)."""
    return TrendInput(
        latest_price=200.0,
        sma_50=190.0,
        sma_150=180.0,
        sma_200=170.0,
        rolling_52w_high=205.0,
    )


def _weak_trend() -> TrendInput:
    """Trend where no checks pass."""
    return TrendInput(
        latest_price=100.0,
        sma_50=120.0,
        sma_150=130.0,
        sma_200=140.0,
        rolling_52w_high=200.0,
    )


def _empty_trend() -> TrendInput:
    """All-None trend (missing data)."""
    return TrendInput()


def _strong_vcp() -> VcpInput:
    return VcpInput(vcp_score=90.0, pattern_detected=True)


def _weak_vcp() -> VcpInput:
    return VcpInput(vcp_score=20.0, pattern_detected=False)


def _empty_vcp() -> VcpInput:
    return VcpInput()


def _strong_volume() -> VolumeInput:
    return VolumeInput(pullback_below_sma=True, volume_dryup=True, no_heavy_selling=True)


def _weak_volume() -> VolumeInput:
    return VolumeInput(pullback_below_sma=False, volume_dryup=False, no_heavy_selling=False)


def _empty_volume() -> VolumeInput:
    return VolumeInput()


def _strong_fundamentals() -> FundamentalsInput:
    return FundamentalsInput(
        revenue_growth_yoy=0.30,
        earnings_growth_yoy=0.40,
        roe=0.25,
        net_margin=0.15,
        debt_equity=0.5,
    )


def _weak_fundamentals() -> FundamentalsInput:
    return FundamentalsInput(
        revenue_growth_yoy=0.02,
        earnings_growth_yoy=0.01,
        roe=0.05,
        net_margin=0.01,
        debt_equity=3.0,
    )


def _empty_fundamentals() -> FundamentalsInput:
    return FundamentalsInput()


# ===================================================================
# TestMcsaResult — dataclass
# ===================================================================

class TestMcsaResult:
    """Tests for the :class:`McsaResult` frozen dataclass."""

    def test_frozen(self):
        r = McsaResult(
            score=50.0, band="neutral", trend_score=10.0,
            vcp_component=15.0, volume_score=10.0, fundamental_score=15.0,
            evidence={}, missing_fields=[],
        )
        with pytest.raises(AttributeError):
            r.score = 99  # type: ignore[misc]

    def test_fields(self):
        r = McsaResult(
            score=82.5, band="watchlist", trend_score=25.0,
            vcp_component=30.0, volume_score=12.0, fundamental_score=15.5,
            evidence={"trend": {}}, missing_fields=["vcp.vcp_score"],
        )
        assert r.score == 82.5
        assert r.band == "watchlist"
        assert r.trend_score == 25.0
        assert r.vcp_component == 30.0
        assert r.volume_score == 12.0
        assert r.fundamental_score == 15.5
        assert r.missing_fields == ["vcp.vcp_score"]


# ===================================================================
# TestTrendScoring
# ===================================================================

class TestTrendScoring:
    """Tests for trend component scoring via compute_mcsa_score."""

    def test_strong_trend_gets_full_weight(self):
        inp = McsaInput(trend=_strong_trend())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.trend_score == 30.0  # full weight_trend

    def test_weak_trend_gets_zero(self):
        inp = McsaInput(trend=_weak_trend())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.trend_score == 0.0

    def test_missing_trend_data_gets_zero(self):
        inp = McsaInput(trend=_empty_trend())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.trend_score == 0.0

    def test_partial_trend_scored(self):
        """Only price > SMA50 true → partial score."""
        trend = TrendInput(
            latest_price=200.0,
            sma_50=190.0,
            sma_150=None,
            sma_200=None,
            rolling_52w_high=None,
        )
        inp = McsaInput(trend=trend)
        result = compute_mcsa_score(inp, _default_cfg())
        # price_above_sma50 (8 out of 30 raw) → 8/30 * 30 = 8.0
        assert result.trend_score == 8.0

    def test_near_52w_high_boundary(self):
        """Price within 15% distance from high → should pass."""
        cfg = _default_cfg()
        trend = TrendInput(
            latest_price=86.0,
            sma_50=None,
            sma_150=None,
            sma_200=None,
            rolling_52w_high=100.0,
        )
        inp = McsaInput(trend=trend)
        result = compute_mcsa_score(inp, cfg)
        # distance = 1 - 86/100 = 0.14, which is <= 0.15 → passes
        assert result.evidence["trend"]["near_52w_high"] is True

    def test_near_52w_high_just_outside(self):
        """Price at 16% distance from high → should not pass."""
        trend = TrendInput(
            latest_price=84.0,
            sma_50=None,
            sma_150=None,
            sma_200=None,
            rolling_52w_high=100.0,
        )
        inp = McsaInput(trend=trend)
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.evidence["trend"]["near_52w_high"] is False


# ===================================================================
# TestVcpScoring
# ===================================================================

class TestVcpScoring:
    """Tests for VCP component scoring."""

    def test_strong_vcp_scores_high(self):
        inp = McsaInput(vcp=_strong_vcp())
        result = compute_mcsa_score(inp, _default_cfg())
        # 90/100 * 35 = 31.5
        assert result.vcp_component == 31.5

    def test_weak_vcp_no_pattern_capped(self):
        """No pattern → capped at no_pattern_cap (15)."""
        inp = McsaInput(vcp=_weak_vcp())
        cfg = _default_cfg()
        result = compute_mcsa_score(inp, cfg)
        # 20/100 * 35 = 7.0, capped at min(7.0, 15.0) = 7.0
        assert result.vcp_component == 7.0

    def test_high_vcp_no_pattern_capped(self):
        """High vcp_score but no pattern → capped at 15."""
        inp = McsaInput(vcp=VcpInput(vcp_score=80.0, pattern_detected=False))
        cfg = _default_cfg()
        result = compute_mcsa_score(inp, cfg)
        # 80/100 * 35 = 28.0, capped at min(28.0, 15.0) = 15.0
        assert result.vcp_component == 15.0

    def test_missing_vcp_gives_zero(self):
        inp = McsaInput(vcp=_empty_vcp())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.vcp_component == 0.0

    def test_perfect_vcp_with_pattern(self):
        inp = McsaInput(vcp=VcpInput(vcp_score=100.0, pattern_detected=True))
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.vcp_component == 35.0  # full weight


# ===================================================================
# TestVolumeScoring
# ===================================================================

class TestVolumeScoring:
    """Tests for volume component scoring."""

    def test_all_volume_signals_true(self):
        inp = McsaInput(volume=_strong_volume())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.volume_score == 15.0  # full weight

    def test_all_volume_signals_false(self):
        inp = McsaInput(volume=_weak_volume())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.volume_score == 0.0

    def test_missing_volume_gives_zero(self):
        inp = McsaInput(volume=_empty_volume())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.volume_score == 0.0

    def test_partial_volume(self):
        """Only volume_dryup true → partial score."""
        vol = VolumeInput(pullback_below_sma=False, volume_dryup=True, no_heavy_selling=False)
        inp = McsaInput(volume=vol)
        result = compute_mcsa_score(inp, _default_cfg())
        # 5/15 * 15 = 5.0
        assert result.volume_score == 5.0


# ===================================================================
# TestFundamentalsScoring
# ===================================================================

class TestFundamentalsScoring:
    """Tests for fundamentals component scoring."""

    def test_all_fundamentals_pass(self):
        inp = McsaInput(fundamentals=_strong_fundamentals())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.fundamental_score == 20.0  # full weight

    def test_all_fundamentals_fail(self):
        inp = McsaInput(fundamentals=_weak_fundamentals())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.fundamental_score == 0.0

    def test_missing_fundamentals_gives_zero(self):
        inp = McsaInput(fundamentals=_empty_fundamentals())
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.fundamental_score == 0.0

    def test_partial_fundamentals(self):
        """Only revenue + earnings pass → partial score."""
        fund = FundamentalsInput(
            revenue_growth_yoy=0.20,
            earnings_growth_yoy=0.25,
            roe=0.05,  # below 0.15 threshold
            net_margin=0.01,  # below 0.05 threshold
            debt_equity=3.0,  # above 1.0 max
        )
        inp = McsaInput(fundamentals=fund)
        result = compute_mcsa_score(inp, _default_cfg())
        # revenue 5 + earnings 5 = 10 out of 20 raw → 10/20 * 20 = 10.0
        assert result.fundamental_score == 10.0


# ===================================================================
# TestBandClassification
# ===================================================================

class TestBandClassification:
    """Tests for band classification via full scoring."""

    def test_strong_band(self):
        """Score >= 85 → strong."""
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        # 30 + 31.5 + 15 + 20 = 96.5
        assert result.band == "strong"

    def test_watchlist_band(self):
        """Score >= 70 and < 85 → watchlist."""
        # Arrange: strong trend (30) + strong vcp (31.5) + weak vol (0) + partial fund (10) = 71.5
        fund = FundamentalsInput(
            revenue_growth_yoy=0.20, earnings_growth_yoy=0.25,
            roe=0.05, net_margin=0.01, debt_equity=3.0,
        )
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_weak_volume(),
            fundamentals=fund,
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.band == "watchlist"

    def test_neutral_band(self):
        """Score >= 50 and < 70 → neutral."""
        # Arrange: strong trend (30) + no_pattern vcp capped (15) + weak vol (0) + weak fund (0) = 45
        # Need something around 50-69... let's try:
        # strong trend (30) + weak vcp w/ pattern (7.0) + strong vol (15) + no fund (0) = 52
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_weak_vcp(),
            volume=_strong_volume(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert 50 <= result.score < 70
        assert result.band == "neutral"

    def test_weak_band(self):
        """Score < 50 → weak."""
        inp = McsaInput()
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.score < 50
        assert result.band == "weak"


# ===================================================================
# TestComputeMcsaScore — integration
# ===================================================================

class TestComputeMcsaScore:
    """Integration tests for :func:`compute_mcsa_score`."""

    def test_perfect_score(self):
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=VcpInput(vcp_score=100.0, pattern_detected=True),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.score == 100.0
        assert result.band == "strong"

    def test_zero_score(self):
        inp = McsaInput()
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.score == 0.0
        assert result.band == "weak"

    def test_component_scores_sum_to_total(self):
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        total = (
            result.trend_score
            + result.vcp_component
            + result.volume_score
            + result.fundamental_score
        )
        assert result.score == pytest.approx(total)

    def test_evidence_has_all_sections(self):
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert "trend" in result.evidence
        assert "vcp" in result.evidence
        assert "volume" in result.evidence
        assert "fundamentals" in result.evidence

    def test_returns_mcsa_result_type(self):
        result = compute_mcsa_score(McsaInput(), _default_cfg())
        assert isinstance(result, McsaResult)

    def test_missing_fields_tracked(self):
        """Empty input → missing fields populated."""
        inp = McsaInput()
        result = compute_mcsa_score(inp, _default_cfg())
        assert len(result.missing_fields) > 0

    def test_no_missing_fields_when_complete(self):
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.missing_fields == []

    def test_score_never_exceeds_100(self):
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=VcpInput(vcp_score=150.0, pattern_detected=True),  # over 100
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.score <= 100.0


# ===================================================================
# TestMissingDataModes
# ===================================================================

class TestMissingDataModes:
    """Tests for missing_data mode behaviour."""

    def test_partial_mode_default(self):
        """Default mode is 'partial' — missing fields contribute 0, no error."""
        cfg = _default_cfg()
        assert cfg.missing_data_mode == "partial"
        inp = McsaInput()
        result = compute_mcsa_score(inp, cfg)
        assert result.score == 0.0
        assert len(result.missing_fields) > 0

    def test_fail_mode_raises_on_missing(self):
        """'fail' mode raises McsaDataError when any field is None."""
        cfg = build_mcsa_config({"missing_data": {"mode": "fail"}})
        inp = McsaInput()  # all None
        with pytest.raises(McsaDataError, match="Missing required fields"):
            compute_mcsa_score(inp, cfg)

    def test_fail_mode_ok_when_complete(self):
        """'fail' mode does NOT raise when all fields present."""
        cfg = build_mcsa_config({"missing_data": {"mode": "fail"}})
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, cfg)
        assert result.missing_fields == []
        assert result.score > 0

    def test_zero_mode_zeroes_components_with_missing_inputs(self):
        """'zero' mode → any component with a missing field gets score 0."""
        cfg = build_mcsa_config({"missing_data": {"mode": "zero"}})
        # trend is complete, everything else is missing
        inp = McsaInput(trend=_strong_trend())
        result = compute_mcsa_score(inp, cfg)
        # trend has no missing fields → full score (30)
        assert result.trend_score == 30.0
        # vcp, volume, fundamentals all have missing inputs → zeroed out
        assert result.vcp_component == 0.0
        assert result.volume_score == 0.0
        assert result.fundamental_score == 0.0

    def test_zero_mode_preserves_complete_components(self):
        """'zero' mode leaves components with no missing fields intact."""
        cfg = build_mcsa_config({"missing_data": {"mode": "zero"}})
        inp = McsaInput(
            trend=_strong_trend(),
            vcp=_strong_vcp(),
            volume=_strong_volume(),
            fundamentals=_strong_fundamentals(),
        )
        result = compute_mcsa_score(inp, cfg)
        assert result.missing_fields == []
        assert result.trend_score == 30.0
        assert result.vcp_component == 31.5
        assert result.volume_score == 15.0
        assert result.fundamental_score == 20.0

    def test_zero_mode_zeros_only_affected_components(self):
        """'zero' mode zeros only components with missing inputs, not all."""
        cfg = build_mcsa_config({"missing_data": {"mode": "zero"}})
        # trend + volume complete; vcp + fundamentals missing
        inp = McsaInput(
            trend=_strong_trend(),
            volume=_strong_volume(),
        )
        result = compute_mcsa_score(inp, cfg)
        assert result.trend_score == 30.0
        assert result.volume_score == 15.0
        assert result.vcp_component == 0.0
        assert result.fundamental_score == 0.0


class TestMissingFieldTracking:
    """Tests for accurate missing field recording."""

    def test_trend_records_both_missing_inputs_when_all_none(self):
        """When all trend inputs are None, all 5 field names appear in missing_fields."""
        inp = McsaInput(trend=_empty_trend())
        result = compute_mcsa_score(inp, _default_cfg())
        missing = result.missing_fields
        assert "trend.latest_price" in missing
        assert "trend.sma_50" in missing
        assert "trend.sma_150" in missing
        assert "trend.sma_200" in missing
        assert "trend.rolling_52w_high" in missing

    def test_trend_records_each_missing_input_independently(self):
        """Each missing input is listed once (deduplicated); present inputs absent."""
        # Only sma_50 is present; latest_price, sma_150, sma_200, rolling_52w_high missing
        trend = TrendInput(sma_50=100.0)
        inp = McsaInput(trend=trend)
        result = compute_mcsa_score(inp, _default_cfg())
        missing = result.missing_fields
        assert "trend.latest_price" in missing
        # sma_50 is present so should not be in missing
        assert "trend.sma_50" not in missing
        assert "trend.sma_150" in missing
        assert "trend.sma_200" in missing
        assert "trend.rolling_52w_high" in missing

    def test_vcp_pattern_detected_none_recorded_as_missing(self):
        """When vcp_score is set but pattern_detected is None, it's recorded as missing."""
        inp = McsaInput(vcp=VcpInput(vcp_score=80.0, pattern_detected=None))
        result = compute_mcsa_score(inp, _default_cfg())
        assert "vcp.pattern_detected" in result.missing_fields

    def test_vcp_pattern_detected_none_no_cap_applied(self):
        """When pattern_detected is None, the no_pattern_cap should NOT be applied."""
        cfg = _default_cfg()
        # 80/100 * 35 = 28.0 — cap is 15; without cap score stays 28.0
        inp = McsaInput(vcp=VcpInput(vcp_score=80.0, pattern_detected=None))
        result = compute_mcsa_score(inp, cfg)
        assert result.vcp_component == 28.0

    def test_vcp_pattern_detected_false_still_applies_cap(self):
        """Explicit pattern_detected=False still triggers the no_pattern_cap."""
        inp = McsaInput(vcp=VcpInput(vcp_score=80.0, pattern_detected=False))
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.vcp_component == 15.0  # capped at 15

    def test_vcp_evidence_records_none_for_missing_pattern_detected(self):
        """evidence['vcp']['pattern_detected'] is None when input is None."""
        inp = McsaInput(vcp=VcpInput(vcp_score=60.0, pattern_detected=None))
        result = compute_mcsa_score(inp, _default_cfg())
        assert result.evidence["vcp"]["pattern_detected"] is None

