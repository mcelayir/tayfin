"""Contraction detection for VCP analysis.

Pure computation functions.  No DB, no network — pure math.

A **contraction** is defined by a pair of consecutive swing highs and the
swing low between them.  The "depth" of a contraction is::

    depth = (swing_high_price − swing_low_price) / swing_high_price

A valid **VCP contraction sequence** exhibits:

1. **Declining swing highs** — each successive swing high is lower than
   (or equal to) the previous one.
2. **Decreasing depth** — each successive contraction is shallower than
   the previous one, meaning volatility is compressing.
3. **At least *min_contractions*** qualifying contractions
   (default: 2, Mark Minervini typically looks for 2-4).

The module also includes a convenience function that starts from raw OHLCV
Series (high / low) and runs the full pipeline:
swing detection → contraction extraction → sequence qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from tayfin_screener_jobs.vcp.swing_detection import (
    SwingPoint,
    detect_swing_highs,
    detect_swing_lows,
)


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Contraction:
    """A single contraction between two consecutive swing highs."""

    high_start: SwingPoint
    """The earlier (higher) swing high that begins this contraction."""
    high_end: SwingPoint
    """The later (lower or equal) swing high that ends this contraction."""
    low_between: SwingPoint | None
    """Deepest swing low between the two highs, if any detected."""
    depth: float
    """Fractional depth: (high_start.price − low_between.price) /
    high_start.price.  0.0 when no swing low exists between the highs."""
    high_decline: float
    """Fractional decline of the ending high relative to the starting high:
    (high_start.price − high_end.price) / high_start.price."""


@dataclass(slots=True)
class ContractionSequence:
    """An ordered sequence of qualifying contractions forming a VCP pattern."""

    contractions: list[Contraction] = field(default_factory=list)
    """Contractions in chronological order."""

    @property
    def count(self) -> int:
        """Number of contractions in the sequence."""
        return len(self.contractions)

    @property
    def depths(self) -> list[float]:
        """List of contraction depths."""
        return [c.depth for c in self.contractions]

    @property
    def total_decline(self) -> float:
        """Overall high decline from first swing high to last."""
        if not self.contractions:
            return 0.0
        first_high = self.contractions[0].high_start.price
        last_high = self.contractions[-1].high_end.price
        if first_high == 0:
            return 0.0
        return (first_high - last_high) / first_high

    @property
    def is_tightening(self) -> bool:
        """True if every successive depth is strictly smaller."""
        d = self.depths
        return all(d[i] > d[i + 1] for i in range(len(d) - 1)) if len(d) >= 2 else False

    def to_dict(self) -> dict:
        """Serialise to a plain dict for features_json storage."""
        return {
            "count": self.count,
            "depths": [round(d, 6) for d in self.depths],
            "total_decline": round(self.total_decline, 6),
            "is_tightening": self.is_tightening,
            "contractions": [
                {
                    "high_start_date": c.high_start.date,
                    "high_start_price": round(c.high_start.price, 4),
                    "high_end_date": c.high_end.date,
                    "high_end_price": round(c.high_end.price, 4),
                    "low_date": c.low_between.date if c.low_between else None,
                    "low_price": round(c.low_between.price, 4) if c.low_between else None,
                    "depth": round(c.depth, 6),
                    "high_decline": round(c.high_decline, 6),
                }
                for c in self.contractions
            ],
        }


# ------------------------------------------------------------------
# Core extraction
# ------------------------------------------------------------------

def extract_contractions(
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
    *,
    max_high_rise: float = 0.02,
) -> list[Contraction]:
    """Extract contraction pairs from sorted swing-high and swing-low lists.

    A contraction is formed by two consecutive swing highs where the later
    high does not rise more than *max_high_rise* fraction above the earlier
    high (default 2 %).  This tolerance allows for near-equal highs which
    are common in real price data.

    Parameters
    ----------
    swing_highs : list[SwingPoint]
        Swing highs sorted chronologically (by .index).
    swing_lows : list[SwingPoint]
        Swing lows sorted chronologically.
    max_high_rise : float
        Maximum fractional rise of the second high relative to the first.
        Set to 0.0 for strict declining-only behaviour.

    Returns
    -------
    list[Contraction]
        Contractions in chronological order.
    """
    contractions: list[Contraction] = []
    for i in range(len(swing_highs) - 1):
        sh1 = swing_highs[i]
        sh2 = swing_highs[i + 1]

        # Second high must not exceed first by more than max_high_rise
        if sh1.price > 0 and (sh2.price - sh1.price) / sh1.price > max_high_rise:
            continue

        # Find the deepest swing low between sh1 and sh2
        low_between = _deepest_low_between(swing_lows, sh1.index, sh2.index)

        if low_between is not None and sh1.price > 0:
            depth = (sh1.price - low_between.price) / sh1.price
        else:
            depth = 0.0

        high_decline = (sh1.price - sh2.price) / sh1.price if sh1.price > 0 else 0.0

        contractions.append(Contraction(
            high_start=sh1,
            high_end=sh2,
            low_between=low_between,
            depth=max(depth, 0.0),
            high_decline=max(high_decline, 0.0),
        ))

    return contractions


def find_contraction_sequence(
    contractions: list[Contraction],
    *,
    min_contractions: int = 2,
    require_tightening: bool = True,
) -> ContractionSequence:
    """Find the longest qualifying contraction sequence.

    Scans the contraction list for the longest run where each successive
    contraction is shallower than the previous (if *require_tightening* is
    True).  The returned sequence has at least *min_contractions* entries
    or is empty.

    Parameters
    ----------
    contractions : list[Contraction]
        Ordered contraction list (from :func:`extract_contractions`).
    min_contractions : int
        Minimum number of contractions for a valid VCP.
    require_tightening : bool
        If True, each depth must be strictly smaller than its predecessor.

    Returns
    -------
    ContractionSequence
        The best (longest) qualifying sequence, or an empty sequence.
    """
    if not contractions:
        return ContractionSequence()

    best: list[Contraction] = []
    current: list[Contraction] = [contractions[0]]

    for i in range(1, len(contractions)):
        prev = current[-1]
        curr = contractions[i]

        # Check continuity: the new contraction must start where the
        # previous one ended (same swing high).
        is_contiguous = curr.high_start.index == prev.high_end.index

        # Check tightening: current depth < previous depth
        is_shallower = curr.depth < prev.depth if require_tightening else True

        if is_contiguous and is_shallower:
            current.append(curr)
        else:
            if len(current) > len(best):
                best = current[:]
            current = [curr]

    if len(current) > len(best):
        best = current

    if len(best) >= min_contractions:
        return ContractionSequence(contractions=best)
    return ContractionSequence()


# ------------------------------------------------------------------
# Convenience pipeline
# ------------------------------------------------------------------

def detect_contractions(
    high: pd.Series,
    low: pd.Series,
    *,
    swing_order: int = 5,
    max_high_rise: float = 0.02,
    min_contractions: int = 2,
    require_tightening: bool = True,
) -> ContractionSequence:
    """End-to-end contraction detection from raw OHLCV high/low series.

    Parameters
    ----------
    high : pd.Series
        High prices indexed by date.
    low : pd.Series
        Low prices indexed by date.
    swing_order : int
        Passed to swing detection (bars on each side).
    max_high_rise : float
        Tolerance for the second high rising above the first.
    min_contractions : int
        Minimum contractions for a valid VCP sequence.
    require_tightening : bool
        Whether each contraction must be shallower than the previous.

    Returns
    -------
    ContractionSequence
        Best qualifying sequence, or empty.
    """
    swing_highs = detect_swing_highs(high, order=swing_order)
    swing_lows = detect_swing_lows(low, order=swing_order)

    contractions = extract_contractions(
        swing_highs, swing_lows, max_high_rise=max_high_rise,
    )

    return find_contraction_sequence(
        contractions,
        min_contractions=min_contractions,
        require_tightening=require_tightening,
    )


# ------------------------------------------------------------------
# Internals
# ------------------------------------------------------------------

def _deepest_low_between(
    swing_lows: list[SwingPoint],
    start_idx: int,
    end_idx: int,
) -> SwingPoint | None:
    """Return the swing low with the lowest price between two bar indices."""
    candidates = [sl for sl in swing_lows if start_idx < sl.index < end_idx]
    if not candidates:
        return None
    return min(candidates, key=lambda sp: sp.price)
