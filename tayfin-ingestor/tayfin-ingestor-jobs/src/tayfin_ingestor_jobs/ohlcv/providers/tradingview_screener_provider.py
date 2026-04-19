"""Bulk OHLCV provider backed by the tradingview-screener Query API.

Makes a single HTTP call to retrieve today's OHLCV snapshot for all
instruments in a given market index, then caches the result in memory.
Subsequent per-ticker calls are served from cache — total HTTP calls: 1.

Historical requests (end_date < today) raise ProviderEmptyError so that
the fallback YfinanceOhlcvProvider handles them transparently.
"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from tradingview_screener import Column, Query

from .base import IOhlcvProvider, ProviderEmptyError

logger = logging.getLogger(__name__)


class TradingViewScreenerOhlcvProvider:
    """OHLCV provider that bulk-fetches all index constituents in one call.

    Parameters
    ----------
    market : str
        tradingview-screener market identifier (e.g. ``'turkey'``).
    index_id : str
        SYML index filter (e.g. ``'SYML:BIST;XU100'``).
    """

    def __init__(self, market: str, index_id: str) -> None:
        self._market = market
        self._index_id = index_id
        self._cache: dict[str, pd.DataFrame] | None = None

    # ------------------------------------------------------------------
    # Public — satisfies IOhlcvProvider Protocol
    # ------------------------------------------------------------------

    def fetch_daily(
        self,
        exchange: str,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        """Return a single-row DataFrame for *symbol* with today's OHLCV.

        Raises
        ------
        ProviderEmptyError
            If ``end_date`` is strictly before today (purely historical
            window), or if the symbol was not found in the screener index.
        """
        today = date.today()

        if end_date is not None:
            try:
                req_end = date.fromisoformat(end_date)
            except ValueError as exc:
                raise ProviderEmptyError(
                    f"Invalid end_date format: {end_date!r}"
                ) from exc
            if req_end < today:
                raise ProviderEmptyError(
                    f"tradingview-screener has no historical bars for {symbol}; "
                    f"end_date {req_end} is before today {today}"
                )

        if self._cache is None:
            self._cache = self._fetch_all()

        bare = symbol.upper()
        df = self._cache.get(bare)
        if df is None:
            raise ProviderEmptyError(
                f"No screener data for {symbol!r} — not in {self._index_id}"
            )
        return df.copy()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_all(self) -> dict[str, pd.DataFrame]:
        """One bulk HTTP call; returns ``{bare_symbol: single-row DataFrame}``."""
        today_str = str(date.today())

        raw_count, raw_df = (
            Query()
            .set_markets(self._market)
            .set_index(self._index_id)
            .select("open", "high", "low", "close", "volume")
            .where(Column("is_primary") == True)  # noqa: E712 — screener uses == True
            .limit(500)
            .get_scanner_data()
        )

        if raw_df.empty:
            raise ProviderEmptyError(
                f"Screener returned empty DataFrame for market={self._market!r}, "
                f"index={self._index_id!r}"
            )

        cache: dict[str, pd.DataFrame] = {}
        for _, row in raw_df.iterrows():
            bare = row["ticker"].split(":")[-1].upper()
            single = pd.DataFrame(
                [
                    {
                        "date": today_str,
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"],
                    }
                ]
            )
            cache[bare] = single

        logger.info(
            "Screener bulk fetch: raw_count=%d, cached=%d symbols",
            raw_count,
            len(cache),
        )
        return cache
