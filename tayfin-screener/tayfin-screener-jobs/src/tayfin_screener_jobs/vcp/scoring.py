"""VCP scoring logic.

Combines contraction, volatility / trend, and volume features into a
composite VCP score (0–100), a confidence tier, and a pattern-detected
boolean.

Pure computation — no DB, no network.

Scoring dimensions
------------------
* **Contraction** (max 35 pts): count, tightening, total decline range.
* **Trend** (max 35 pts): MA alignment, 52-week-high proximity, ATR
  trend, SMA-50 slope.
* **Volume** (max 30 pts): volume dryup, volume trend, volume
  contraction from peak.
"""

from __future__ import annotations

from dataclasses import dataclass

# ------------------------------------------------------------------
# Dimension ceilings
# ------------------------------------------------------------------
MAX_CONTRACTION_SCORE: int = 35
MAX_TREND_SCORE: int = 35
MAX_VOLUME_SCORE: int = 30

# ------------------------------------------------------------------
# Thresholds for pattern detection & confidence tiers
# ------------------------------------------------------------------
PATTERN_SCORE_THRESHOLD: float = 50.0
HIGH_CONFIDENCE_THRESHOLD: float = 70.0
MEDIUM_CONFIDENCE_THRESHOLD: float = 50.0


# ------------------------------------------------------------------
# Result data class
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScoringResult:
    """Immutable container for the output of :func:`compute_vcp_score`."""

    score: float
    """Composite VCP score in [0, 100]."""
    confidence: str
    """Confidence tier: ``"high"``, ``"medium"``, or ``"low"``."""
    pattern_detected: bool
    """True when score ≥ threshold **and** ≥ 2 contractions found."""
    breakdown: dict
    """Sub-scores per dimension: ``contraction``, ``trend``, ``volume``."""


# ------------------------------------------------------------------
# Sub-scoring: contractions  (max 35)
# ------------------------------------------------------------------

def score_contractions(features: dict) -> float:
    """Score contraction features.

    Expected keys
    ~~~~~~~~~~~~~
    * ``count`` — number of contractions (int)
    * ``is_tightening`` — whether depths are strictly decreasing (bool)
    * ``total_decline`` — fractional decline from first to last swing
      high (float, 0–1)

    Scoring
    ~~~~~~~
    * **Count** (0–15): 1 → 3, 2 → 8, 3 → 12, 4+ → 15
    * **Tightening** (0–10): +10 when tightening and count ≥ 2
    * **Total decline** (0–10): ideal range 10–35 % → 10, near-ideal
      5–10 % or 35–50 % → 5
    """
    score = 0.0
    count = features.get("count", 0)

    # --- count ---
    if count >= 4:
        score += 15.0
    elif count == 3:
        score += 12.0
    elif count == 2:
        score += 8.0
    elif count == 1:
        score += 3.0

    # --- tightening ---
    if features.get("is_tightening", False) and count >= 2:
        score += 10.0

    # --- total decline ---
    total_decline = features.get("total_decline", 0.0)
    if 0.10 <= total_decline <= 0.35:
        score += 10.0
    elif 0.05 <= total_decline < 0.10:
        score += 5.0
    elif 0.35 < total_decline <= 0.50:
        score += 5.0

    return min(score, MAX_CONTRACTION_SCORE)


# ------------------------------------------------------------------
# Sub-scoring: trend / volatility  (max 35)
# ------------------------------------------------------------------

def score_trend(features: dict) -> float:
    """Score volatility / trend features.

    Expected keys
    ~~~~~~~~~~~~~
    * ``ma_alignment`` — bullish MA order (bool)
    * ``near_52w_high`` — within 25 % of 52-week high (bool)
    * ``atr_trend`` — normalised ATR slope (float, negative = good)
    * ``sma_50_slope`` — fractional SMA-50 change (float, positive = good)

    Scoring
    ~~~~~~~
    * **MA alignment** (0–15): +15 when True
    * **52-week high** (0–10): +10 when True
    * **ATR trend** (0–5): < −10 % → 5, < 0 → 3
    * **SMA-50 slope** (0–5): > 5 % → 5, > 0 → 3
    """
    score = 0.0

    if features.get("ma_alignment", False):
        score += 15.0

    if features.get("near_52w_high", False):
        score += 10.0

    atr_trend = features.get("atr_trend", 0.0)
    if atr_trend < -0.10:
        score += 5.0
    elif atr_trend < 0.0:
        score += 3.0

    sma_slope = features.get("sma_50_slope", 0.0)
    if sma_slope > 0.05:
        score += 5.0
    elif sma_slope > 0.0:
        score += 3.0

    return min(score, MAX_TREND_SCORE)


# ------------------------------------------------------------------
# Sub-scoring: volume  (max 30)
# ------------------------------------------------------------------

def score_volume(features: dict) -> float:
    """Score volume features.

    Expected keys
    ~~~~~~~~~~~~~
    * ``volume_dryup`` — whether recent vol < threshold of longer avg (bool)
    * ``volume_trend`` — normalised vol slope (float, negative = good)
    * ``volume_contraction_pct`` — decline from peak (float, 0–1)

    Scoring
    ~~~~~~~
    * **Volume dryup** (0–15): +15 when True
    * **Volume trend** (0–5): < −10 % → 5, < 0 → 3
    * **Volume contraction %** (0–10): ≥ 50 % → 10, ≥ 30 % → 6, ≥ 15 % → 3
    """
    score = 0.0

    if features.get("volume_dryup", False):
        score += 15.0

    vol_trend = features.get("volume_trend", 0.0)
    if vol_trend < -0.10:
        score += 5.0
    elif vol_trend < 0.0:
        score += 3.0

    vol_contraction = features.get("volume_contraction_pct", 0.0)
    if vol_contraction >= 0.50:
        score += 10.0
    elif vol_contraction >= 0.30:
        score += 6.0
    elif vol_contraction >= 0.15:
        score += 3.0

    return min(score, MAX_VOLUME_SCORE)


# ------------------------------------------------------------------
# Confidence tier
# ------------------------------------------------------------------

def _determine_confidence(
    total_score: float,
    contraction_features: dict,
    trend_features: dict,
    volume_features: dict,
) -> str:
    """Return ``"high"``, ``"medium"``, or ``"low"`` confidence tier.

    **High** requires:
    * total score ≥ 70
    * at least 2 tightening contractions
    * MA alignment
    * near 52-week high

    **Medium** requires total score ≥ 50.

    Everything else is **low**.
    """
    if (
        total_score >= HIGH_CONFIDENCE_THRESHOLD
        and contraction_features.get("count", 0) >= 2
        and contraction_features.get("is_tightening", False)
        and trend_features.get("ma_alignment", False)
        and trend_features.get("near_52w_high", False)
    ):
        return "high"
    if total_score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


# ------------------------------------------------------------------
# Public API — composite scoring
# ------------------------------------------------------------------

def compute_vcp_score(
    *,
    contraction_features: dict,
    volatility_features: dict,
    volume_features: dict,
) -> ScoringResult:
    """Compute a composite VCP score from all feature dicts.

    Parameters
    ----------
    contraction_features
        Dict produced by
        :meth:`ContractionSequence.to_dict` — must contain
        ``count``, ``is_tightening``, ``total_decline``.
    volatility_features
        Dict produced by :func:`extract_volatility_features` — must
        contain ``ma_alignment``, ``near_52w_high``, ``atr_trend``,
        ``sma_50_slope``.
    volume_features
        Dict produced by :func:`extract_volume_features` — must
        contain ``volume_dryup``, ``volume_trend``,
        ``volume_contraction_pct``.

    Returns
    -------
    ScoringResult
        Composite score, confidence, pattern_detected flag, and
        per-dimension breakdown.
    """
    contraction_score = score_contractions(contraction_features)
    trend_score = score_trend(volatility_features)
    volume_score = score_volume(volume_features)

    total = round(contraction_score + trend_score + volume_score, 2)

    confidence = _determine_confidence(
        total,
        contraction_features,
        volatility_features,
        volume_features,
    )

    pattern_detected = (
        total >= PATTERN_SCORE_THRESHOLD
        and contraction_features.get("count", 0) >= 2
    )

    return ScoringResult(
        score=total,
        confidence=confidence,
        pattern_detected=pattern_detected,
        breakdown={
            "contraction": round(contraction_score, 2),
            "trend": round(trend_score, 2),
            "volume": round(volume_score, 2),
        },
    )
