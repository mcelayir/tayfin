"""Unit tests for TradingViewScreenerOhlcvProvider and ohlcv_provider_factory.

All tests are fully offline — the tradingview_screener.Query chain is mocked.
No network calls, no database connections.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tayfin_ingestor_jobs.ohlcv.normalize import normalize_ohlcv_df
from tayfin_ingestor_jobs.ohlcv.providers.base import ProviderEmptyError
from tayfin_ingestor_jobs.ohlcv.providers.factory import ohlcv_provider_factory
from tayfin_ingestor_jobs.ohlcv.providers.tradingview_provider import (
    TradingViewOhlcvProvider,
)
from tayfin_ingestor_jobs.ohlcv.providers.tradingview_screener_provider import (
    TradingViewScreenerOhlcvProvider,
)

# ---------------------------------------------------------------------------
# Helpers & constants
# ---------------------------------------------------------------------------

MOCK_SCREENER_DF = pd.DataFrame(
    [
        {
            "ticker": "BIST:AKBNK",
            "open": 42.5,
            "high": 44.0,
            "low": 41.0,
            "close": 43.2,
            "volume": 1_500_000,
        },
        {
            "ticker": "BIST:THYAO",
            "open": 310.0,
            "high": 320.0,
            "low": 305.0,
            "close": 315.0,
            "volume": 8_000_000,
        },
    ]
)
MOCK_RAW_COUNT = 2

MOCK_TARGET = (
    "tayfin_ingestor_jobs.ohlcv.providers.tradingview_screener_provider.Query"
)


def _make_query_mock():
    """Build a fully-chained mock of tradingview_screener.Query."""
    mock_q = MagicMock()
    # Every chained method must return the same mock so the chain works.
    mock_q.return_value = mock_q
    mock_q.set_markets.return_value = mock_q
    mock_q.set_index.return_value = mock_q
    mock_q.select.return_value = mock_q
    mock_q.where.return_value = mock_q
    mock_q.limit.return_value = mock_q
    mock_q.get_scanner_data.return_value = (MOCK_RAW_COUNT, MOCK_SCREENER_DF.copy())
    return mock_q


# ---------------------------------------------------------------------------
# Tests: TradingViewScreenerOhlcvProvider
# ---------------------------------------------------------------------------


class TestTradingViewScreenerOhlcvProvider:
    def _make_provider(self) -> TradingViewScreenerOhlcvProvider:
        return TradingViewScreenerOhlcvProvider(
            market="turkey", index_id="SYML:BIST;XU100"
        )

    def test_fetch_daily_makes_one_bulk_call(self):
        """Fetching two different tickers must call get_scanner_data exactly once."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            provider.fetch_daily("BIST", "AKBNK")
            provider.fetch_daily("BIST", "THYAO")

        mock_q.get_scanner_data.assert_called_once()

    def test_fetch_daily_returns_correct_columns(self):
        """Returned DataFrame must have exactly the normalized input columns."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            df = provider.fetch_daily("BIST", "AKBNK")

        assert set(df.columns) == {"date", "open", "high", "low", "close", "volume"}

    def test_fetch_daily_returns_correct_values(self):
        """Values must match the mock screener row for AKBNK."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            df = provider.fetch_daily("BIST", "AKBNK")

        assert len(df) == 1
        row = df.iloc[0]
        assert row["open"] == pytest.approx(42.5)
        assert row["high"] == pytest.approx(44.0)
        assert row["low"] == pytest.approx(41.0)
        assert row["close"] == pytest.approx(43.2)
        assert row["volume"] == 1_500_000

    def test_fetch_daily_strips_exchange_prefix(self):
        """Fetching 'AKBNK' works even though the screener returns 'BIST:AKBNK'."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            df = provider.fetch_daily("BIST", "AKBNK")

        assert len(df) == 1

    def test_fetch_daily_date_is_today(self):
        """The 'date' column must be stamped with today's date string."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            df = provider.fetch_daily("BIST", "THYAO")

        assert df.iloc[0]["date"] == str(date.today())

    def test_fetch_daily_historical_raises_provider_empty_error(self):
        """A window ending strictly before today must raise ProviderEmptyError."""
        yesterday = str(date.today() - timedelta(days=1))
        provider = self._make_provider()
        with pytest.raises(ProviderEmptyError, match="no historical bars"):
            provider.fetch_daily("BIST", "AKBNK", end_date=yesterday)

    def test_fetch_daily_missing_ticker_raises_provider_empty_error(self):
        """A symbol absent from the screener result must raise ProviderEmptyError."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            with pytest.raises(ProviderEmptyError):
                provider.fetch_daily("BIST", "UNKNWN")

    def test_normalize_accepts_provider_output(self):
        """normalize_ohlcv_df must not raise on valid screener provider output."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            df = provider.fetch_daily("BIST", "AKBNK")

        # normalize_ohlcv_df should return without raising
        result = normalize_ohlcv_df(df)
        assert not result.empty

    def test_no_http_call_on_construction(self):
        """Instantiating the provider makes zero HTTP calls."""
        mock_q = _make_query_mock()
        with patch(MOCK_TARGET, mock_q):
            self._make_provider()

        mock_q.get_scanner_data.assert_not_called()

    def test_empty_screener_response_raises(self):
        """An empty DataFrame from the screener must raise ProviderEmptyError."""
        mock_q = _make_query_mock()
        mock_q.get_scanner_data.return_value = (0, pd.DataFrame())
        with patch(MOCK_TARGET, mock_q):
            provider = self._make_provider()
            with pytest.raises(ProviderEmptyError, match="empty"):
                provider.fetch_daily("BIST", "AKBNK")


# ---------------------------------------------------------------------------
# Tests: ohlcv_provider_factory
# ---------------------------------------------------------------------------


class TestOhlcvProviderFactory:
    def test_factory_returns_screener_for_bist(self):
        """TR/BIST config must return TradingViewScreenerOhlcvProvider."""
        provider = ohlcv_provider_factory({"country": "TR", "index_code": "BIST"})
        assert isinstance(provider, TradingViewScreenerOhlcvProvider)

    def test_factory_returns_per_ticker_for_nasdaq(self):
        """US/NDX config must return TradingViewOhlcvProvider."""
        provider = ohlcv_provider_factory({"country": "US", "index_code": "NDX"})
        assert isinstance(provider, TradingViewOhlcvProvider)

    def test_factory_returns_per_ticker_for_empty_config(self):
        """Empty config must default to TradingViewOhlcvProvider (safe fallback)."""
        provider = ohlcv_provider_factory({})
        assert isinstance(provider, TradingViewOhlcvProvider)

    def test_factory_is_case_insensitive(self):
        """Lowercase country / index_code must still route correctly."""
        provider = ohlcv_provider_factory({"country": "tr", "index_code": "bist"})
        assert isinstance(provider, TradingViewScreenerOhlcvProvider)

    def test_factory_unknown_market_returns_per_ticker(self):
        """An unrecognised market must return TradingViewOhlcvProvider."""
        provider = ohlcv_provider_factory({"country": "UK", "index_code": "UKX"})
        assert isinstance(provider, TradingViewOhlcvProvider)

    def test_screener_provider_params(self):
        """TradingViewScreenerOhlcvProvider must be configured with correct market/index."""
        provider = ohlcv_provider_factory({"country": "TR", "index_code": "BIST"})
        assert isinstance(provider, TradingViewScreenerOhlcvProvider)
        assert provider._market == "turkey"
        assert provider._index_id == "SYML:BIST;XU100"
