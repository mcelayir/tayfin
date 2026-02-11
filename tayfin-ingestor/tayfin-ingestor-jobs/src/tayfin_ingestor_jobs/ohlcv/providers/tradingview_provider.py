"""TradingView OHLCV provider — primary source for daily candles."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pandas as pd

from .base import (
    PermanentProviderError,
    ProviderEmptyError,
    TransientProviderError,
)
from ..reliability import RateLimiter

logger = logging.getLogger(__name__)

# Strings in exceptions that indicate transient (retryable) failures
_TRANSIENT_KEYWORDS = (
    "timeout", "timed out", "connection reset", "connection refused",
    "connection error", "429", "rate limit", "too many requests",
    "temporarily unavailable", "service unavailable", "eof",
    "broken pipe", "websocket",
)


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _TRANSIENT_KEYWORDS)


class TradingViewOhlcvProvider:
    """Fetch daily OHLCV via ``tradingview-scraper`` Streamer.

    Uses the ``Streamer`` class with ``export_result=True`` which returns
    a dict ``{"ohlc": [...], "indicator": {...}}``.

    Timeframe MUST be lowercase ``"1d"`` for daily candles — uppercase
    ``"1D"`` silently defaults to 1-minute in the library.
    """

    TIMEFRAME = "1d"

    def __init__(self, cookie: str | None = None, rate_limiter: RateLimiter | None = None):
        self._cookie = cookie or os.environ.get("TRADINGVIEW_COOKIE")
        self._rate_limiter = rate_limiter or RateLimiter()

    # ------------------------------------------------------------------
    # IOhlcvProvider
    # ------------------------------------------------------------------

    def fetch_daily(
        self,
        exchange: str,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        """Fetch daily candles from TradingView.

        ``start_date`` / ``end_date`` are not natively supported by the
        Streamer API — it works with a candle count.  Post-fetch filtering
        is applied when date bounds are provided.

        Raises
        ------
        PermanentProviderError
            If the library is not installed.
        TransientProviderError
            On network / websocket / rate-limit failures.
        ProviderEmptyError
            If no data is returned.
        """
        try:
            from tradingview_scraper.symbols.stream import Streamer
        except ImportError as exc:
            raise PermanentProviderError(
                "tradingview-scraper is not installed.  "
                "pip install tradingview-scraper"
            ) from exc

        logger.info(
            "TradingView fetch — exchange=%s symbol=%s limit=%d",
            exchange, symbol, limit,
        )

        # Rate-limit between ticker fetches
        self._rate_limiter.wait()

        try:
            streamer = Streamer(export_result=True, export_type="json")
            result = streamer.stream(
                exchange=exchange,
                symbol=symbol,
                timeframe=self.TIMEFRAME,
                numb_price_candles=limit,
            )
        except Exception as exc:
            if _is_transient(exc):
                raise TransientProviderError(
                    f"TradingView transient error for {exchange}:{symbol}: {exc}"
                ) from exc
            raise PermanentProviderError(
                f"TradingView stream failed for {exchange}:{symbol}: {exc}"
            ) from exc

        ohlc = result.get("ohlc") if isinstance(result, dict) else None
        if not ohlc:
            raise ProviderEmptyError(
                f"TradingView returned no OHLC data for {exchange}:{symbol}"
            )

        rows = []
        for candle in ohlc:
            ts = candle.get("timestamp")
            if ts is None:
                continue
            dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append(
                {
                    "date": dt_str,
                    "open": candle.get("open"),
                    "high": candle.get("high"),
                    "low": candle.get("low"),
                    "close": candle.get("close"),
                    "volume": candle.get("volume"),
                }
            )

        if not rows:
            raise ProviderEmptyError(
                f"TradingView returned empty candles for {exchange}:{symbol}"
            )

        df = pd.DataFrame(rows)

        # Post-fetch date filtering
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]

        if df.empty:
            raise ProviderEmptyError(
                f"TradingView returned no candles in date range for {exchange}:{symbol}"
            )

        logger.info(
            "TradingView — %s:%s → %d candles (%s → %s)",
            exchange, symbol, len(df),
            df["date"].min(), df["date"].max(),
        )
        return df
