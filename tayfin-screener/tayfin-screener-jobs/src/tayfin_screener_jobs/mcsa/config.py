"""MCSA configuration dataclass and builder.

Reads the ``mcsa`` section from the screener YAML config, applies defaults
from ADR-01, validates weights sum to 100, and returns a typed McsaConfig.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TrendSignalConfig:
    """Points awarded for each trend condition."""

    price_above_sma50: int = 8
    sma50_above_sma150: int = 8
    sma150_above_sma200: int = 8
    near_52w_high: int = 6
    near_52w_high_max_distance_pct: float = 0.15


@dataclass(frozen=True, slots=True)
class VcpComponentConfig:
    """Weights for the VCP / base quality component."""

    no_pattern_cap: float = 15.0


@dataclass(frozen=True, slots=True)
class VolumeSignalConfig:
    """Points and thresholds for volume quality signals."""

    sma_window: int = 50
    lookback_days: int = 20
    pullback_below_sma_points: int = 5
    dryup_points: int = 5
    dryup_threshold_pct: float = 0.5
    no_heavy_selling_points: int = 5
    heavy_selling_threshold_pct: float = 1.5


@dataclass(frozen=True, slots=True)
class FundamentalsConfig:
    """Thresholds and points for each fundamentals signal."""

    revenue_growth_min_pct: float = 0.15
    revenue_growth_points: int = 5
    earnings_growth_min_pct: float = 0.15
    earnings_growth_points: int = 5
    roe_min_pct: float = 0.15
    roe_points: int = 4
    net_margin_min_pct: float = 0.05
    net_margin_points: int = 3
    debt_equity_max_value: float = 1.0
    debt_equity_points: int = 3


@dataclass(frozen=True, slots=True)
class BandsConfig:
    """Score-band thresholds."""

    strong_min: int = 85
    watchlist_min: int = 70
    neutral_min: int = 50


@dataclass(frozen=True, slots=True)
class LookbacksConfig:
    """Max-age-in-days for input data sources."""

    trend_days: int = 7
    volume_days: int = 7
    vcp_days: int = 7
    fundamentals_days: int = 90


@dataclass(frozen=True, slots=True)
class McsaConfig:
    """Top-level MCSA configuration container."""

    # Component weights (must sum to 100)
    weight_trend: int = 30
    weight_vcp: int = 35
    weight_volume: int = 15
    weight_fundamentals: int = 20

    trend: TrendSignalConfig = field(default_factory=TrendSignalConfig)
    vcp: VcpComponentConfig = field(default_factory=VcpComponentConfig)
    volume: VolumeSignalConfig = field(default_factory=VolumeSignalConfig)
    fundamentals: FundamentalsConfig = field(default_factory=FundamentalsConfig)
    bands: BandsConfig = field(default_factory=BandsConfig)
    lookbacks: LookbacksConfig = field(default_factory=LookbacksConfig)

    # Missing data mode: "partial" | "zero" | "fail"
    missing_data_mode: str = "partial"


class McsaConfigError(ValueError):
    """Raised when MCSA configuration is invalid."""


def build_mcsa_config(raw: dict | None) -> McsaConfig:
    """Build an ``McsaConfig`` from a raw dict (the ``mcsa`` section).

    Applies defaults for any missing keys and validates that weights sum
    to exactly 100.
    """
    if not raw:
        return McsaConfig()

    weights = raw.get("weights", {})
    trend_raw = raw.get("trend", {})
    vcp_raw = raw.get("vcp", {})
    volume_raw = raw.get("volume", {})
    fund_raw = raw.get("fundamentals", {})
    bands_raw = raw.get("bands", {})
    lookbacks_raw = raw.get("lookbacks", {})
    missing_mode = raw.get("missing_data", {}).get("mode", "partial")

    trend_cfg = TrendSignalConfig(
        price_above_sma50=_get_points(trend_raw, "price_above_sma50", 8),
        sma50_above_sma150=_get_points(trend_raw, "sma50_above_sma150", 8),
        sma150_above_sma200=_get_points(trend_raw, "sma150_above_sma200", 8),
        near_52w_high=_get_points(trend_raw, "near_52w_high", 6),
        near_52w_high_max_distance_pct=trend_raw.get("near_52w_high", {}).get(
            "max_distance_pct", 0.15
        ),
    )

    vcp_cfg = VcpComponentConfig(
        no_pattern_cap=float(vcp_raw.get("no_pattern_cap", 15)),
    )

    volume_cfg = VolumeSignalConfig(
        sma_window=int(volume_raw.get("sma_window", 50)),
        lookback_days=int(volume_raw.get("lookback_days", 20)),
        pullback_below_sma_points=_get_points(volume_raw, "pullback_below_sma", 5),
        dryup_points=_get_points(volume_raw, "dryup", 5),
        dryup_threshold_pct=float(
            volume_raw.get("dryup", {}).get("threshold_pct", 0.5)
        ),
        no_heavy_selling_points=_get_points(volume_raw, "no_heavy_selling", 5),
        heavy_selling_threshold_pct=float(
            volume_raw.get("no_heavy_selling", {}).get(
                "heavy_selling_threshold_pct", 1.5
            )
        ),
    )

    fund_cfg = FundamentalsConfig(
        revenue_growth_min_pct=float(
            fund_raw.get("revenue_growth", {}).get("min_pct", 0.15)
        ),
        revenue_growth_points=int(
            fund_raw.get("revenue_growth", {}).get("points", 5)
        ),
        earnings_growth_min_pct=float(
            fund_raw.get("earnings_growth", {}).get("min_pct", 0.15)
        ),
        earnings_growth_points=int(
            fund_raw.get("earnings_growth", {}).get("points", 5)
        ),
        roe_min_pct=float(fund_raw.get("roe", {}).get("min_pct", 0.15)),
        roe_points=int(fund_raw.get("roe", {}).get("points", 4)),
        net_margin_min_pct=float(
            fund_raw.get("net_margin", {}).get("min_pct", 0.05)
        ),
        net_margin_points=int(fund_raw.get("net_margin", {}).get("points", 3)),
        debt_equity_max_value=float(
            fund_raw.get("debt_equity", {}).get("max_value", 1.0)
        ),
        debt_equity_points=int(fund_raw.get("debt_equity", {}).get("points", 3)),
    )

    bands_cfg = BandsConfig(
        strong_min=int(bands_raw.get("strong_min", 85)),
        watchlist_min=int(bands_raw.get("watchlist_min", 70)),
        neutral_min=int(bands_raw.get("neutral_min", 50)),
    )

    lookbacks_cfg = LookbacksConfig(
        trend_days=int(lookbacks_raw.get("trend_days", 7)),
        volume_days=int(lookbacks_raw.get("volume_days", 7)),
        vcp_days=int(lookbacks_raw.get("vcp_days", 7)),
        fundamentals_days=int(lookbacks_raw.get("fundamentals_days", 90)),
    )

    cfg = McsaConfig(
        weight_trend=int(weights.get("trend", 30)),
        weight_vcp=int(weights.get("vcp", 35)),
        weight_volume=int(weights.get("volume", 15)),
        weight_fundamentals=int(weights.get("fundamentals", 20)),
        trend=trend_cfg,
        vcp=vcp_cfg,
        volume=volume_cfg,
        fundamentals=fund_cfg,
        bands=bands_cfg,
        lookbacks=lookbacks_cfg,
        missing_data_mode=str(missing_mode),
    )

    _validate(cfg)
    return cfg


# ------------------------------------------------------------------
# internal helpers
# ------------------------------------------------------------------


def _get_points(section: dict, key: str, default: int) -> int:
    """Extract ``points`` from a nested signal dict."""
    val = section.get(key, {})
    if isinstance(val, dict):
        return int(val.get("points", default))
    return default


def _validate(cfg: McsaConfig) -> None:
    total = (
        cfg.weight_trend
        + cfg.weight_vcp
        + cfg.weight_volume
        + cfg.weight_fundamentals
    )
    if total != 100:
        raise McsaConfigError(
            f"MCSA weights must sum to 100, got {total} "
            f"(trend={cfg.weight_trend}, vcp={cfg.weight_vcp}, "
            f"volume={cfg.weight_volume}, fundamentals={cfg.weight_fundamentals})"
        )

    if cfg.missing_data_mode not in ("partial", "zero", "fail"):
        raise McsaConfigError(
            f"Invalid missing_data.mode: {cfg.missing_data_mode!r} "
            "(expected: partial | zero | fail)"
        )
