"""ScreenerClient edge-case tests — timeout, retry, error propagation.

These tests patch httpx.get at the lowest level to simulate network failures,
429/503 retries, and unexpected 5xx errors.
"""

from __future__ import annotations

import pytest
import httpx

from tayfin_bff.clients.screener_client import ScreenerClient


# ── Helpers ──────────────────────────────────────────────────────────


class FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, status_code: int, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


# ── Connection & timeout tests ───────────────────────────────────────


class TestConnectionFailure:
    def test_returns_none_after_all_retries(self, monkeypatch):
        """Client returns None after exhausting retries on ConnectError."""
        call_count = 0

        def fake_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(httpx, "get", fake_get)
        # Patch sleep to avoid actual delays
        monkeypatch.setattr("time.sleep", lambda _: None)

        client = ScreenerClient(base_url="http://fake:8020", max_retries=2)
        result = client.get_mcsa_latest_all()

        assert result is None
        # 1 initial + 2 retries = 3 total
        assert call_count == 3

    def test_timeout_returns_none(self, monkeypatch):
        """Client returns None on timeout after retries."""
        call_count = 0

        def fake_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timed out")

        monkeypatch.setattr(httpx, "get", fake_get)
        monkeypatch.setattr("time.sleep", lambda _: None)

        client = ScreenerClient(base_url="http://fake:8020", max_retries=1)
        result = client.get_mcsa_latest_ticker("AAPL")

        assert result is None
        assert call_count == 2  # 1 + 1 retry


# ── Retry behavior ──────────────────────────────────────────────────


class TestRetryBehavior:
    def test_retries_on_429(self, monkeypatch):
        """Client retries on 429 and succeeds if next request is OK."""
        attempts = []

        def fake_get(*args, **kwargs):
            attempts.append(1)
            if len(attempts) <= 2:
                return FakeResponse(429, text="rate limited")
            return FakeResponse(200, json_data={"items": []})

        monkeypatch.setattr(httpx, "get", fake_get)
        monkeypatch.setattr("time.sleep", lambda _: None)

        client = ScreenerClient(base_url="http://fake:8020", max_retries=3)
        result = client.get_mcsa_latest_all()

        assert result == {"items": []}
        assert len(attempts) == 3

    def test_retries_on_503(self, monkeypatch):
        """Client retries on 503 and succeeds."""
        attempts = []

        def fake_get(*args, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, json_data={"ticker": "BKR"})

        monkeypatch.setattr(httpx, "get", fake_get)
        monkeypatch.setattr("time.sleep", lambda _: None)

        client = ScreenerClient(base_url="http://fake:8020", max_retries=2)
        result = client.get_mcsa_latest_ticker("BKR")

        assert result == {"ticker": "BKR"}
        assert len(attempts) == 2

    def test_gives_up_after_max_retries_on_429(self, monkeypatch):
        """Client returns None if 429 persists beyond max_retries."""
        attempts = []

        def fake_get(*args, **kwargs):
            attempts.append(1)
            return FakeResponse(429, text="rate limited")

        monkeypatch.setattr(httpx, "get", fake_get)
        monkeypatch.setattr("time.sleep", lambda _: None)

        client = ScreenerClient(base_url="http://fake:8020", max_retries=2)
        result = client.get_mcsa_latest_all()

        # After max_retries, loop breaks with a 429 → status >= 400 → returns None
        assert result is None


# ── Error propagation ────────────────────────────────────────────────


class TestErrorPropagation:
    def test_500_returns_none(self, monkeypatch):
        """Client returns None on 500 (no retry for non-429/503)."""
        def fake_get(*args, **kwargs):
            return FakeResponse(500, text="internal error")

        monkeypatch.setattr(httpx, "get", fake_get)

        client = ScreenerClient(base_url="http://fake:8020")
        result = client.get_mcsa_latest_all()

        assert result is None

    def test_404_with_allow_returns_none(self, monkeypatch):
        """Ticker endpoint returns None on 404 (expected for missing tickers)."""
        def fake_get(*args, **kwargs):
            return FakeResponse(404, text="not found")

        monkeypatch.setattr(httpx, "get", fake_get)

        client = ScreenerClient(base_url="http://fake:8020")
        result = client.get_mcsa_latest_ticker("ZZZZ")

        assert result is None

    def test_successful_json_parsing(self, monkeypatch):
        """Client correctly parses valid JSON response."""
        expected = {"items": [{"ticker": "AAPL", "score": 85}]}

        def fake_get(*args, **kwargs):
            return FakeResponse(200, json_data=expected)

        monkeypatch.setattr(httpx, "get", fake_get)

        client = ScreenerClient(base_url="http://fake:8020")
        result = client.get_mcsa_latest_all()

        assert result == expected

    def test_env_var_base_url(self, monkeypatch):
        """Client reads base URL from environment variable."""
        monkeypatch.setenv("TAYFIN_SCREENER_API_BASE_URL", "http://custom:9999")

        client = ScreenerClient()
        assert client.base_url == "http://custom:9999"

    def test_base_url_trailing_slash_stripped(self):
        """Client strips trailing slash from base URL."""
        client = ScreenerClient(base_url="http://example.com:8020/")
        assert client.base_url == "http://example.com:8020"
