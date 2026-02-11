"""Shared helpers for fundamentals providers."""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd


def safe_float(val: Any) -> Optional[float]:
    """Convert *val* to float safely; return None on failure."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return None
            return float(val)
        if isinstance(val, str):
            v = val.strip().replace(",", "").upper()
            if v in ("", "N/A", "NONE"):
                return None
            if v.endswith("B"):
                return float(v[:-1]) * 1_000_000_000
            if v.endswith("M"):
                return float(v[:-1]) * 1_000_000
            if v.endswith("K"):
                return float(v[:-1]) * 1_000
            return float(v)
        return float(val)
    except Exception:
        return None


def div(n: Optional[float], d: Optional[float]) -> Optional[float]:
    """Safe division; return None when denominator is zero or None."""
    if n is None or d in (None, 0):
        return None
    try:
        return float(n) / float(d)
    except Exception:
        return None
