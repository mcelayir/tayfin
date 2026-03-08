"""MCSA scoring module — pure computation, no I/O.

Implements the Minervini Chartist Scoring Algorithm (ADR-01):
  mcsa_score = trend_score + vcp_component + volume_score + fundamental_score

Each component is weighted and normalized according to ``McsaConfig``.
All inputs arrive as plain dicts/dataclasses; the module never touches
databases, HTTP, or the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tayfin_screener_jobs.mcsa.config import McsaConfig


# ------------------------------------------------------------------
# Input / output data structures
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrendInput:
    """Latest price and moving averages for trend scoring."""

    latest_price: float | None = None
    sma_50: float | None = None
    sma_150: float | None = None
    sma_200: float | None = None
    rolling_52w_high: float | None = None


@dataclass(frozen=True, slots=True)
class VcpInput:
    """Latest VCP screening result."""

    vcp_score: float | None = None
    pattern_detected: bool | None = None


@dataclass(frozen=True, slots=True)
class VolumeInput:
    """Pre-computed volume quality flags from ``volume_assessment``."""

    pullback_below_sma: bool | None = None
    volume_dryup: bool | None = None
    no_heavy_selling: bool | None = None


@dataclass(frozen=True, slots=True)
class FundamentalsInput:
    """Latest fundamentals snapshot values."""

    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    roe: float | None = None
    net_margin: float | None = None
    debt_equity: float | None = None


@dataclass(frozen=True, slots=True)
class McsaInput:
    """Aggregated inputs for one ticker."""

    trend: TrendInput = field(default_factory=TrendInput)
    vcp: VcpInput = field(default_factory=VcpInput)
    volume: VolumeInput = field(default_factory=VolumeInput)
    fundamentals: FundamentalsInput = field(default_factory=FundamentalsInput)


@dataclass(frozen=True, slots=True)
class McsaResult:
    """Scoring output for one ticker."""

    score: float  # 0–100
    band: str  # "strong" | "watchlist" | "neutral" | "weak"
    trend_score: float
    vcp_component: float
    volume_score: float
    fundamental_score: float
    evidence: dict
    missing_fields: list[str]


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def compute_mcsa_score(inp: McsaInput, cfg: McsaConfig) -> McsaResult:
    """Compute the composite MCSA score for a single ticker.

    Parameters
    ----------
    inp : McsaInput
        All input values for the ticker.
    cfg : McsaConfig
        Algorithm configuration (weights, thresholds, mode).

    Returns
    -------
    McsaResult
        Composite score, band, per-component scores, evidence, missing fields.

    Raises
    ------
    McsaDataError
        When ``missing_data.mode == 'fail'`` and any required field is None.
    """
    missing: list[str] = []

    trend_score, trend_evidence = _score_trend(inp.trend, cfg, missing)
    vcp_score, vcp_evidence = _score_vcp(inp.vcp, cfg, missing)
    volume_score, volume_evidence = _score_volume(inp.volume, cfg, missing)
    fund_score, fund_evidence = _score_fundamentals(inp.fundamentals, cfg, missing)

    if cfg.missing_data_mode == "fail" and missing:
        raise McsaDataError(
            f"Missing required fields in 'fail' mode: {missing}"
        )

    if cfg.missing_data_mode == "zero" and missing:
        # Zero out component scores that have any missing required inputs.
        if any(f.startswith("trend.") for f in missing):
            trend_score = 0.0
        if any(f.startswith("vcp.") for f in missing):
            vcp_score = 0.0
        if any(f.startswith("volume.") for f in missing):
            volume_score = 0.0
        if any(f.startswith("fundamentals.") for f in missing):
            fund_score = 0.0

    total = trend_score + vcp_score + volume_score + fund_score

    band = _classify_band(total, cfg)

    evidence = {
        "trend": trend_evidence,
        "vcp": vcp_evidence,
        "volume": volume_evidence,
        "fundamentals": fund_evidence,
        "total_score": round(total, 2),
        "band": band,
    }

    return McsaResult(
        score=round(total, 2),
        band=band,
        trend_score=round(trend_score, 2),
        vcp_component=round(vcp_score, 2),
        volume_score=round(volume_score, 2),
        fundamental_score=round(fund_score, 2),
        evidence=evidence,
        missing_fields=missing,
    )


class McsaDataError(Exception):
    """Raised when required input data is missing in ``fail`` mode."""


# ------------------------------------------------------------------
# Component scorers
# ------------------------------------------------------------------


def _score_trend(
    t: TrendInput, cfg: McsaConfig, missing: list[str]
) -> tuple[float, dict]:
    """Score the trend-structure component (max = weight_trend)."""
    tc = cfg.trend
    max_raw = (
        tc.price_above_sma50
        + tc.sma50_above_sma150
        + tc.sma150_above_sma200
        + tc.near_52w_high
    )

    raw = 0.0
    evidence: dict = {}

    # Price > SMA50
    if t.latest_price is not None and t.sma_50 is not None:
        flag = t.latest_price > t.sma_50
        evidence["price_above_sma50"] = flag
        if flag:
            raw += tc.price_above_sma50
    else:
        evidence["price_above_sma50"] = None
        if t.latest_price is None:
            _note_missing(missing, "trend.latest_price", cfg)
        if t.sma_50 is None:
            _note_missing(missing, "trend.sma_50", cfg)

    # SMA50 > SMA150
    if t.sma_50 is not None and t.sma_150 is not None:
        flag = t.sma_50 > t.sma_150
        evidence["sma50_above_sma150"] = flag
        if flag:
            raw += tc.sma50_above_sma150
    else:
        evidence["sma50_above_sma150"] = None
        if t.sma_50 is None:
            _note_missing(missing, "trend.sma_50", cfg)
        if t.sma_150 is None:
            _note_missing(missing, "trend.sma_150", cfg)

    # SMA150 > SMA200
    if t.sma_150 is not None and t.sma_200 is not None:
        flag = t.sma_150 > t.sma_200
        evidence["sma150_above_sma200"] = flag
        if flag:
            raw += tc.sma150_above_sma200
    else:
        evidence["sma150_above_sma200"] = None
        if t.sma_150 is None:
            _note_missing(missing, "trend.sma_150", cfg)
        if t.sma_200 is None:
            _note_missing(missing, "trend.sma_200", cfg)

    # Price within max_distance_pct of rolling 52-week high
    if t.latest_price is not None and t.rolling_52w_high is not None:
        distance = 1.0 - (t.latest_price / t.rolling_52w_high) if t.rolling_52w_high > 0 else 1.0
        evidence["distance_to_52w_high_pct"] = round(distance, 4)
        flag = distance <= tc.near_52w_high_max_distance_pct
        evidence["near_52w_high"] = flag
        if flag:
            raw += tc.near_52w_high
    else:
        evidence["distance_to_52w_high_pct"] = None
        evidence["near_52w_high"] = None
        if t.latest_price is None:
            _note_missing(missing, "trend.latest_price", cfg)
        if t.rolling_52w_high is None:
            _note_missing(missing, "trend.rolling_52w_high", cfg)

    # Normalize raw → weighted score
    score = (raw / max_raw) * cfg.weight_trend if max_raw > 0 else 0.0
    evidence["score"] = round(score, 2)
    return score, evidence


def _score_vcp(
    v: VcpInput, cfg: McsaConfig, missing: list[str]
) -> tuple[float, dict]:
    """Score the VCP / base-quality component (max = weight_vcp)."""
    evidence: dict = {}

    if v.vcp_score is None:
        evidence["vcp_score"] = None
        evidence["pattern_detected"] = None
        evidence["score"] = 0.0
        _note_missing(missing, "vcp.vcp_score", cfg)
        return 0.0, evidence

    # Normalize vcp_score (0–100) → 0–1
    normalized = max(0.0, min(v.vcp_score / 100.0, 1.0))
    score = normalized * cfg.weight_vcp

    # Apply no-pattern cap only when pattern_detected is explicitly known
    if v.pattern_detected is None:
        evidence["pattern_detected"] = None
        _note_missing(missing, "vcp.pattern_detected", cfg)
    else:
        pattern_detected = bool(v.pattern_detected)
        if not pattern_detected:
            score = min(score, cfg.vcp.no_pattern_cap)
        evidence["pattern_detected"] = pattern_detected

    evidence["vcp_score"] = v.vcp_score
    evidence["score"] = round(score, 2)
    return score, evidence


def _score_volume(
    vol: VolumeInput, cfg: McsaConfig, missing: list[str]
) -> tuple[float, dict]:
    """Score the volume-quality component (max = weight_volume)."""
    vc = cfg.volume
    max_raw = (
        vc.pullback_below_sma_points
        + vc.dryup_points
        + vc.no_heavy_selling_points
    )

    raw = 0.0
    evidence: dict = {}

    # Pullback below SMA
    if vol.pullback_below_sma is not None:
        evidence["pullback_below_sma"] = vol.pullback_below_sma
        if vol.pullback_below_sma:
            raw += vc.pullback_below_sma_points
    else:
        evidence["pullback_below_sma"] = None
        _note_missing(missing, "volume.pullback_below_sma", cfg)

    # Volume dry-up
    if vol.volume_dryup is not None:
        evidence["volume_dryup"] = vol.volume_dryup
        if vol.volume_dryup:
            raw += vc.dryup_points
    else:
        evidence["volume_dryup"] = None
        _note_missing(missing, "volume.volume_dryup", cfg)

    # No heavy selling
    if vol.no_heavy_selling is not None:
        evidence["no_heavy_selling"] = vol.no_heavy_selling
        if vol.no_heavy_selling:
            raw += vc.no_heavy_selling_points
    else:
        evidence["no_heavy_selling"] = None
        _note_missing(missing, "volume.no_heavy_selling", cfg)

    score = (raw / max_raw) * cfg.weight_volume if max_raw > 0 else 0.0
    evidence["score"] = round(score, 2)
    return score, evidence


def _score_fundamentals(
    f: FundamentalsInput, cfg: McsaConfig, missing: list[str]
) -> tuple[float, dict]:
    """Score the fundamentals component (max = weight_fundamentals)."""
    fc = cfg.fundamentals
    max_raw = (
        fc.revenue_growth_points
        + fc.earnings_growth_points
        + fc.roe_points
        + fc.net_margin_points
        + fc.debt_equity_points
    )

    raw = 0.0
    evidence: dict = {}

    # Revenue growth YoY
    if f.revenue_growth_yoy is not None:
        evidence["revenue_growth_yoy"] = f.revenue_growth_yoy
        if f.revenue_growth_yoy >= fc.revenue_growth_min_pct:
            raw += fc.revenue_growth_points
    else:
        evidence["revenue_growth_yoy"] = None
        _note_missing(missing, "fundamentals.revenue_growth_yoy", cfg)

    # Earnings growth YoY
    if f.earnings_growth_yoy is not None:
        evidence["earnings_growth_yoy"] = f.earnings_growth_yoy
        if f.earnings_growth_yoy >= fc.earnings_growth_min_pct:
            raw += fc.earnings_growth_points
    else:
        evidence["earnings_growth_yoy"] = None
        _note_missing(missing, "fundamentals.earnings_growth_yoy", cfg)

    # ROE
    if f.roe is not None:
        evidence["roe"] = f.roe
        if f.roe >= fc.roe_min_pct:
            raw += fc.roe_points
    else:
        evidence["roe"] = None
        _note_missing(missing, "fundamentals.roe", cfg)

    # Net margin
    if f.net_margin is not None:
        evidence["net_margin"] = f.net_margin
        if f.net_margin >= fc.net_margin_min_pct:
            raw += fc.net_margin_points
    else:
        evidence["net_margin"] = None
        _note_missing(missing, "fundamentals.net_margin", cfg)

    # Debt / Equity
    if f.debt_equity is not None:
        evidence["debt_equity"] = f.debt_equity
        if f.debt_equity <= fc.debt_equity_max_value:
            raw += fc.debt_equity_points
    else:
        evidence["debt_equity"] = None
        _note_missing(missing, "fundamentals.debt_equity", cfg)

    score = (raw / max_raw) * cfg.weight_fundamentals if max_raw > 0 else 0.0
    evidence["score"] = round(score, 2)
    return score, evidence


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _classify_band(score: float, cfg: McsaConfig) -> str:
    """Assign a human-readable band label."""
    if score >= cfg.bands.strong_min:
        return "strong"
    if score >= cfg.bands.watchlist_min:
        return "watchlist"
    if score >= cfg.bands.neutral_min:
        return "neutral"
    return "weak"


def _note_missing(missing: list[str], field_name: str, cfg: McsaConfig) -> None:
    """Track a missing field (deduplicated)."""
    if field_name not in missing:
        missing.append(field_name)
