"""OHLCV normalization — clean and validate provider output."""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Raised when OHLCV data fails validation after cleaning."""


def normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw provider DataFrame into canonical OHLCV columns.

    Input columns expected: date, open, high, low, close, volume
    Output columns:         as_of_date, open, high, low, close, volume

    Rules applied (in order):
    1. Rename ``date`` → ``as_of_date``.
    2. Drop rows where ``close`` is NaN.
    3. De-duplicate by ``as_of_date`` (keep last).
    4. Sort ascending by ``as_of_date``.
    5. Cast numerics — prices to float, volume to int.
    6. Assert prices > 0, high >= low, volume >= 0.

    Raises
    ------
    NormalizationError
        If the DataFrame is empty after cleaning, or invariants are violated.
    """
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise NormalizationError(f"Missing columns in provider output: {missing}")

    out = df.copy()

    # 1. Rename
    out = out.rename(columns={"date": "as_of_date"})

    # 2. Drop NaN close
    before = len(out)
    out = out.dropna(subset=["close"])
    dropped = before - len(out)
    if dropped:
        logger.info("normalize: dropped %d rows with NaN close", dropped)

    # 3. Dedupe
    out = out.drop_duplicates(subset=["as_of_date"], keep="last")

    # 4. Sort
    out = out.sort_values("as_of_date").reset_index(drop=True)

    if out.empty:
        raise NormalizationError("DataFrame empty after cleaning")

    # 5. Cast numerics
    for col in ("open", "high", "low", "close"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype(int)

    # Re-drop rows that became NaN after coercion
    out = out.dropna(subset=["open", "high", "low", "close"])
    if out.empty:
        raise NormalizationError("DataFrame empty after numeric coercion")

    # 6. Invariants
    bad_prices = out[(out["open"] <= 0) | (out["high"] <= 0) | (out["low"] <= 0) | (out["close"] <= 0)]
    if not bad_prices.empty:
        logger.warning("normalize: dropping %d rows with non-positive prices", len(bad_prices))
        out = out[(out["open"] > 0) & (out["high"] > 0) & (out["low"] > 0) & (out["close"] > 0)]

    bad_hl = out[out["high"] < out["low"]]
    if not bad_hl.empty:
        raise NormalizationError(
            f"{len(bad_hl)} rows have high < low — data integrity issue"
        )

    bad_vol = out[out["volume"] < 0]
    if not bad_vol.empty:
        raise NormalizationError(
            f"{len(bad_vol)} rows have negative volume"
        )

    if out.empty:
        raise NormalizationError("DataFrame empty after invariant checks")

    # Final column order
    out = out[["as_of_date", "open", "high", "low", "close", "volume"]].copy()
    return out
