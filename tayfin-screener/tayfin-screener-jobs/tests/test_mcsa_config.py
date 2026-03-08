"""Tests for tayfin_screener_jobs.mcsa.config."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.mcsa.config import (
    BandsConfig,
    FundamentalsConfig,
    LookbacksConfig,
    McsaConfig,
    McsaConfigError,
    TrendSignalConfig,
    VcpComponentConfig,
    VolumeSignalConfig,
    build_mcsa_config,
)


# ===================================================================
# TestBuildMcsaConfig — defaults
# ===================================================================

class TestBuildDefaults:
    """Calling build_mcsa_config with None or {} returns ADR-01 defaults."""

    def test_none_returns_defaults(self):
        cfg = build_mcsa_config(None)
        assert cfg.weight_trend == 30
        assert cfg.weight_vcp == 35
        assert cfg.weight_volume == 15
        assert cfg.weight_fundamentals == 20

    def test_empty_dict_returns_defaults(self):
        cfg = build_mcsa_config({})
        assert cfg.weight_trend == 30
        assert cfg.weight_vcp == 35

    def test_default_trend_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.trend.price_above_sma50 == 8
        assert cfg.trend.sma50_above_sma150 == 8
        assert cfg.trend.sma150_above_sma200 == 8
        assert cfg.trend.near_52w_high == 6
        assert cfg.trend.near_52w_high_max_distance_pct == 0.15

    def test_default_vcp_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.vcp.no_pattern_cap == 15.0

    def test_default_volume_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.volume.sma_window == 50
        assert cfg.volume.lookback_days == 20
        assert cfg.volume.pullback_below_sma_points == 5
        assert cfg.volume.dryup_points == 5
        assert cfg.volume.dryup_threshold_pct == 0.5
        assert cfg.volume.no_heavy_selling_points == 5
        assert cfg.volume.heavy_selling_threshold_pct == 1.5

    def test_default_fundamentals_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.fundamentals.revenue_growth_min_pct == 0.15
        assert cfg.fundamentals.revenue_growth_points == 5
        assert cfg.fundamentals.debt_equity_max_value == 1.0

    def test_default_bands_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.bands.strong_min == 85
        assert cfg.bands.watchlist_min == 70
        assert cfg.bands.neutral_min == 50

    def test_default_lookbacks_config(self):
        cfg = build_mcsa_config(None)
        assert cfg.lookbacks.trend_days == 7
        assert cfg.lookbacks.fundamentals_days == 90

    def test_default_missing_data_mode(self):
        cfg = build_mcsa_config(None)
        assert cfg.missing_data_mode == "partial"


# ===================================================================
# TestBuildMcsaConfig — overrides
# ===================================================================

class TestBuildOverrides:
    """Overriding individual keys changes only those values."""

    def test_custom_weights(self):
        cfg = build_mcsa_config({
            "weights": {"trend": 25, "vcp": 40, "volume": 15, "fundamentals": 20},
        })
        assert cfg.weight_trend == 25
        assert cfg.weight_vcp == 40

    def test_custom_bands(self):
        cfg = build_mcsa_config({
            "bands": {"strong_min": 90, "watchlist_min": 75, "neutral_min": 55},
        })
        assert cfg.bands.strong_min == 90
        assert cfg.bands.watchlist_min == 75
        assert cfg.bands.neutral_min == 55

    def test_custom_missing_data_mode(self):
        cfg = build_mcsa_config({"missing_data": {"mode": "fail"}})
        assert cfg.missing_data_mode == "fail"


# ===================================================================
# TestBuildMcsaConfig — validation
# ===================================================================

class TestBuildValidation:
    """build_mcsa_config raises McsaConfigError on invalid input."""

    def test_weights_not_summing_to_100(self):
        with pytest.raises(McsaConfigError, match="must sum to 100"):
            build_mcsa_config({
                "weights": {"trend": 30, "vcp": 30, "volume": 15, "fundamentals": 20},
            })

    def test_invalid_missing_data_mode(self):
        with pytest.raises(McsaConfigError, match="Invalid missing_data.mode"):
            build_mcsa_config({"missing_data": {"mode": "ignore"}})


# ===================================================================
# TestFrozenDataclasses
# ===================================================================

class TestFrozenDataclasses:
    """All config dataclasses should be frozen."""

    def test_mcsa_config_frozen(self):
        cfg = McsaConfig()
        with pytest.raises(AttributeError):
            cfg.weight_trend = 50  # type: ignore[misc]

    def test_trend_signal_config_frozen(self):
        c = TrendSignalConfig()
        with pytest.raises(AttributeError):
            c.price_above_sma50 = 99  # type: ignore[misc]

    def test_volume_signal_config_frozen(self):
        c = VolumeSignalConfig()
        with pytest.raises(AttributeError):
            c.dryup_points = 99  # type: ignore[misc]

    def test_fundamentals_config_frozen(self):
        c = FundamentalsConfig()
        with pytest.raises(AttributeError):
            c.revenue_growth_points = 99  # type: ignore[misc]

    def test_bands_config_frozen(self):
        c = BandsConfig()
        with pytest.raises(AttributeError):
            c.strong_min = 99  # type: ignore[misc]

    def test_lookbacks_config_frozen(self):
        c = LookbacksConfig()
        with pytest.raises(AttributeError):
            c.trend_days = 99  # type: ignore[misc]

    def test_vcp_component_config_frozen(self):
        c = VcpComponentConfig()
        with pytest.raises(AttributeError):
            c.no_pattern_cap = 99.0  # type: ignore[misc]
