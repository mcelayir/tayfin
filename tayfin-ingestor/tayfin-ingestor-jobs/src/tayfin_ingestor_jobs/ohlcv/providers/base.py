"""Provider interface for OHLCV data."""
from __future__ import annotations

from typing import Protocol

import pandas as pd


class ProviderError(Exception):
    """Base exception for OHLCV provider failures."""


class ProviderEmptyError(ProviderError):
    """Provider returned no data."""


class IOhlcvProvider(Protocol):
    """Contract for OHLCV data providers.

    ``fetch_daily`` MUST return a DataFrame with columns:
        date, open, high, low, close, volume
    """

    def fetch_daily(
        self,
        exchange: str,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV candles.

        Parameters
        ----------
        exchange : str
            Exchange code (e.g. ``NASDAQ``).
        symbol : str
            Bare ticker (e.g. ``AAPL``).
        start_date / end_date : str | None
            ISO date bounds (inclusive). Providers may ignore if they only
            support a candle-count parameter.
        limit : int
            Maximum number of candles to request.

        Returns
        -------
        pd.DataFrame
            Columns: date, open, high, low, close, volume.

        Raises
        ------
        ProviderEmptyError
            If no data is returned.
        ProviderError
            On transport / parsing failures.
        """
        ...
