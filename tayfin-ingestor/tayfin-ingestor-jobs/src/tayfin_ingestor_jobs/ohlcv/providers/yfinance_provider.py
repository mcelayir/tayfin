"""yfinance OHLCV provider — fallback source for daily candles."""
from __future__ import annotations

import logging

import pandas as pd

from .base import (
    PermanentProviderError,
    ProviderEmptyError,
    TransientProviderError,
)

logger = logging.getLogger(__name__)

_TRANSIENT_KEYWORDS = (
    "timeout", "timed out", "connection reset", "connection refused",
    "connection error", "429", "rate limit", "too many requests",
    "service unavailable", "eof", "broken pipe",
)


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _TRANSIENT_KEYWORDS)


class YfinanceOhlcvProvider:
    """Fetch daily OHLCV via ``yfinance``.

    Uses ``yfinance.Ticker(symbol).history(start=..., end=..., interval='1d')``.
    The ``exchange`` parameter is accepted for interface compatibility but is
    not used — yfinance resolves symbols globally.
    """

    def fetch_daily(
        self,
        exchange: str,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise PermanentProviderError(
                "yfinance is not installed.  pip install yfinance"
            ) from exc

        logger.info("yfinance fetch — symbol=%s start=%s end=%s", symbol, start_date, end_date)

        try:
            ticker = yf.Ticker(symbol)
            kwargs: dict = {"interval": "1d"}
            if start_date:
                kwargs["start"] = start_date
            if end_date:
                kwargs["end"] = end_date
            if not start_date and not end_date:
                kwargs["period"] = "2y"

            hist = ticker.history(**kwargs)
        except Exception as exc:
            if _is_transient(exc):
                raise TransientProviderError(
                    f"yfinance transient error for {symbol}: {exc}"
                ) from exc
            raise PermanentProviderError(
                f"yfinance history failed for {symbol}: {exc}"
            ) from exc

        if hist is None or hist.empty:
            raise ProviderEmptyError(f"yfinance returned no data for {symbol}")

        # yfinance returns a DatetimeIndex; normalize to our schema
        df = pd.DataFrame(
            {
                "date": hist.index.strftime("%Y-%m-%d"),
                "open": hist["Open"].values,
                "high": hist["High"].values,
                "low": hist["Low"].values,
                "close": hist["Close"].values,
                "volume": hist["Volume"].values,
            }
        )

        if df.empty:
            raise ProviderEmptyError(f"yfinance returned empty frame for {symbol}")

        logger.info(
            "yfinance — %s → %d candles (%s → %s)",
            symbol, len(df), df["date"].min(), df["date"].max(),
        )
        return df
