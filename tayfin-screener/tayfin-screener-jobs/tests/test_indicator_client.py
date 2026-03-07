"""Tests for IndicatorClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from tayfin_screener_jobs.clients.indicator_client import IndicatorClient


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
# get_latest
# ------------------------------------------------------------------

class TestGetLatest:
    """Tests for get_latest."""

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_success_returns_dict(self, mock_get):
        payload = {
            "ticker": "AAPL",
            "as_of_date": "2026-03-06",
            "indicator": "sma",
            "params": {"window": 50},
            "value": 174.35,
            "source": "computed",
        }
        mock_get.return_value = _mock_response(200, payload)
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_latest("AAPL", "sma", window=50)

        assert result is not None
        assert result["value"] == 174.35
        assert result["indicator"] == "sma"
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["ticker"] == "AAPL"
        assert kwargs["params"]["indicator"] == "sma"
        assert kwargs["params"]["window"] == 50

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_404_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_latest("AAPL", "sma", window=50)

        assert result is None

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_window_omitted_when_none(self, mock_get):
        mock_get.return_value = _mock_response(200, {"value": 1.0})
        client = IndicatorClient(base_url="http://test:8001")
        client.get_latest("AAPL", "atr")

        _, kwargs = mock_get.call_args
        assert "window" not in kwargs["params"]


# ------------------------------------------------------------------
# get_range
# ------------------------------------------------------------------

class TestGetRange:
    """Tests for get_range."""

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_success_returns_items(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "ticker": "AAPL",
            "indicator": "sma",
            "from": "2025-01-01",
            "to": "2025-03-01",
            "params": {"window": 20},
            "items": [
                {"as_of_date": "2025-01-02", "value": 170.5},
                {"as_of_date": "2025-01-03", "value": 171.2},
            ],
        })
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_range("AAPL", "sma", "2025-01-01", "2025-03-01", window=20)

        assert len(result) == 2
        assert result[0]["value"] == 170.5
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["from"] == "2025-01-01"
        assert kwargs["params"]["to"] == "2025-03-01"
        assert kwargs["params"]["window"] == 20

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_404_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_range("NOSYMBOL", "sma", "2025-01-01", "2025-03-01")

        assert result == []


# ------------------------------------------------------------------
# get_index_latest
# ------------------------------------------------------------------

class TestGetIndexLatest:
    """Tests for get_index_latest."""

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_success_returns_items(self, mock_get):
        mock_get.return_value = _mock_response(200, {
            "index_code": "NDX",
            "indicator": "sma",
            "params": {"window": 50},
            "items": [
                {"ticker": "AAPL", "as_of_date": "2026-03-06", "value": 174.35},
                {"ticker": "GOOGL", "as_of_date": "2026-03-06", "value": 162.40},
            ],
        })
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_index_latest("NDX", "sma", window=50)

        assert len(result) == 2
        assert result[0]["ticker"] == "AAPL"
        _, kwargs = mock_get.call_args
        assert "/indicators/index/latest" in mock_get.call_args[0][0]
        assert kwargs["params"]["index_code"] == "NDX"

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_404_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_response(404)
        client = IndicatorClient(base_url="http://test:8001")
        result = client.get_index_latest("UNKNOWN", "sma")

        assert result == []

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_window_omitted_when_none(self, mock_get):
        mock_get.return_value = _mock_response(200, {"items": []})
        client = IndicatorClient(base_url="http://test:8001")
        client.get_index_latest("NDX", "atr")

        _, kwargs = mock_get.call_args
        assert "window" not in kwargs["params"]


# ------------------------------------------------------------------
# retry behaviour
# ------------------------------------------------------------------

class TestRetry:
    """Tests for retry on 429 / 503."""

    @patch("tayfin_screener_jobs.clients.indicator_client.time.sleep")
    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _mock_response(429),
            _mock_response(200, {"value": 1.0}),
        ]
        client = IndicatorClient(base_url="http://test:8001", max_retries=3)
        result = client.get_latest("AAPL", "sma", window=50)

        assert result is not None
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("tayfin_screener_jobs.clients.indicator_client.httpx.get")
    def test_500_raises_immediately(self, mock_get):
        mock_get.return_value = _mock_response(500)
        client = IndicatorClient(base_url="http://test:8001")

        with pytest.raises(httpx.HTTPStatusError):
            client.get_latest("AAPL", "sma")

        assert mock_get.call_count == 1


# ------------------------------------------------------------------
# config
# ------------------------------------------------------------------

class TestConfig:
    """Tests for client configuration."""

    def test_default_base_url(self):
        client = IndicatorClient()
        assert client.base_url == "http://localhost:8010"

    @patch.dict("os.environ", {"TAYFIN_INDICATOR_API_BASE_URL": "http://indicator:9001/"})
    def test_base_url_from_env(self):
        client = IndicatorClient()
        assert client.base_url == "http://indicator:9001"  # trailing slash stripped

    def test_explicit_base_url_overrides_env(self):
        client = IndicatorClient(base_url="http://custom:1234/")
        assert client.base_url == "http://custom:1234"
