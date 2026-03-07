"""Tests for IngestorClient."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import httpx
import pytest

from tayfin_screener_jobs.clients.ingestor_client import IngestorClient


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data: dict | None = None):
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ------------------------------------------------------------------
# get_index_members
# ------------------------------------------------------------------

class TestGetIndexMembers:
    """Tests for get_index_members."""

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_success_returns_items(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "index_code": "NDX",
            "country": "US",
            "count": 2,
            "items": [
                {"instrument_id": "id-1", "symbol": "AAPL", "country": "US"},
                {"instrument_id": "id-2", "symbol": "GOOGL", "country": "US"},
            ],
        })
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_index_members("NDX")

        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[1]["symbol"] == "GOOGL"
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "/indices/members" in args[0]
        assert kwargs["params"]["index_code"] == "NDX"

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_404_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_index_members("UNKNOWN")

        assert result == []

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_passes_country_param(self, mock_get):
        mock_get.return_value = _mock_response(200, {"items": []})
        client = IngestorClient(base_url="http://test:8000")
        client.get_index_members("NDX", country="TR")

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["country"] == "TR"

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_limit_set_to_max(self, mock_get):
        mock_get.return_value = _mock_response(200, {"items": []})
        client = IngestorClient(base_url="http://test:8000")
        client.get_index_members("NDX")

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 5000


# ------------------------------------------------------------------
# get_ohlcv_range
# ------------------------------------------------------------------

class TestGetOhlcvRange:
    """Tests for get_ohlcv_range."""

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_success_returns_items(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "ticker": "AAPL",
            "from": "2025-01-01",
            "to": "2025-03-01",
            "count": 1,
            "items": [
                {
                    "ticker": "AAPL",
                    "as_of_date": "2025-01-02",
                    "open": 170.0,
                    "high": 172.5,
                    "low": 169.0,
                    "close": 171.3,
                    "volume": 85_000_000,
                    "source": "yfinance",
                },
            ],
        })
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_ohlcv_range("AAPL", "2025-01-01", "2025-03-01")

        assert len(result) == 1
        assert result[0]["close"] == 171.3
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["ticker"] == "AAPL"
        assert kwargs["params"]["from"] == "2025-01-01"
        assert kwargs["params"]["to"] == "2025-03-01"

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_404_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_ohlcv_range("NOSYMBOL", "2025-01-01", "2025-03-01")

        assert result == []


# ------------------------------------------------------------------
# retry behaviour
# ------------------------------------------------------------------

class TestRetry:
    """Tests for retry on 429 / 503."""

    @patch("tayfin_screener_jobs.clients.ingestor_client.time.sleep")
    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _mock_response(429),
            _mock_response(200, {"items": [{"symbol": "AAPL"}]}),
        ]
        client = IngestorClient(base_url="http://test:8000", max_retries=3)
        result = client.get_index_members("NDX")

        assert len(result) == 1
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # 1.0 * 2^0

    @patch("tayfin_screener_jobs.clients.ingestor_client.time.sleep")
    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_retries_on_503_with_backoff(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _mock_response(503),
            _mock_response(503),
            _mock_response(200, {"items": []}),
        ]
        client = IngestorClient(base_url="http://test:8000", max_retries=3)
        client.get_index_members("NDX")

        assert mock_get.call_count == 3
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])

    @patch("tayfin_screener_jobs.clients.ingestor_client.time.sleep")
    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_retries_exhausted_raises(self, mock_get, mock_sleep):
        mock_get.return_value = _mock_response(503)
        client = IngestorClient(base_url="http://test:8000", max_retries=2)

        with pytest.raises(httpx.HTTPStatusError):
            client.get_ohlcv_range("AAPL", "2025-01-01", "2025-03-01")

        # 1 initial + 2 retries = 3 calls
        assert mock_get.call_count == 3

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_500_raises_immediately(self, mock_get):
        mock_get.return_value = _mock_response(500)
        client = IngestorClient(base_url="http://test:8000")

        with pytest.raises(httpx.HTTPStatusError):
            client.get_index_members("NDX")

        assert mock_get.call_count == 1


# ------------------------------------------------------------------
# config
# ------------------------------------------------------------------

class TestConfig:
    """Tests for client configuration."""

    def test_default_base_url(self):
        client = IngestorClient()
        assert client.base_url == "http://localhost:8000"

    @patch.dict("os.environ", {"TAYFIN_INGESTOR_API_BASE_URL": "http://ingestor:9000/"})
    def test_base_url_from_env(self):
        client = IngestorClient()
        assert client.base_url == "http://ingestor:9000"  # trailing slash stripped

    def test_explicit_base_url_overrides_env(self):
        client = IngestorClient(base_url="http://custom:1234/")
        assert client.base_url == "http://custom:1234"

    def test_custom_timeout(self):
        client = IngestorClient(timeout_s=5.0)
        assert client.timeout == httpx.Timeout(5.0)


# ------------------------------------------------------------------
# get_fundamentals_latest
# ------------------------------------------------------------------

class TestGetFundamentalsLatest:
    """Tests for get_fundamentals_latest."""

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_success_returns_dict(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "revenue_growth_yoy": 0.25,
            "earnings_growth_yoy": 0.30,
            "roe": 0.20,
            "net_margin": 0.12,
            "debt_equity": 0.5,
        })
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_fundamentals_latest("AAPL")

        assert result is not None
        assert result["revenue_growth_yoy"] == 0.25
        assert result["roe"] == 0.20
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["symbol"] == "AAPL"
        assert kwargs["params"]["country"] == "US"
        assert kwargs["params"]["source"] == "stockdex"

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_404_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IngestorClient(base_url="http://test:8000")
        result = client.get_fundamentals_latest("NOSYMBOL")
        assert result is None

    @patch("tayfin_screener_jobs.clients.ingestor_client.httpx.get")
    def test_custom_country_and_source(self, mock_get):
        mock_get.return_value = _mock_response(200, {})
        client = IngestorClient(base_url="http://test:8000")
        client.get_fundamentals_latest("THYAO", country="TR", source="custom")

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["country"] == "TR"
        assert kwargs["params"]["source"] == "custom"
