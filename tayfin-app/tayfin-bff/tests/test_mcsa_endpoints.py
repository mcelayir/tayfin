"""BFF MCSA endpoint tests — Flask test client with monkeypatched ScreenerClient.

No real network.  All upstream responses are stubbed.
"""

from __future__ import annotations

import pytest

from tayfin_bff.app import create_app

# ── Deterministic fake data ──────────────────────────────────────────

_SEED_DASHBOARD = {
    "items": [
        {
            "ticker": "AAPL",
            "instrument_id": "550e8400-e29b-41d4-a716-446655440000",
            "as_of_date": "2026-03-06",
            "mcsa_score": 82.5,
            "mcsa_band": "watchlist",
            "trend_score": 25.0,
            "vcp_component": 28.0,
            "volume_score": 12.0,
            "fundamental_score": 17.5,
            "evidence": {
                "trend": {"score": 25.0, "price_above_sma50": True},
                "vcp": {"score": 28.0, "pattern_detected": True},
                "volume": {"score": 12.0},
                "fundamentals": {"score": 17.5},
            },
            "missing_fields": [],
        },
        {
            "ticker": "MSFT",
            "instrument_id": None,
            "as_of_date": "2026-03-06",
            "mcsa_score": 45.0,
            "mcsa_band": "weak",
            "trend_score": 10.0,
            "vcp_component": 15.0,
            "volume_score": 5.0,
            "fundamental_score": 15.0,
            "evidence": {"trend": {"score": 10.0}},
            "missing_fields": ["vcp.vcp_score"],
        },
    ]
}

_SEED_TICKER = {
    "ticker": "AAPL",
    "instrument_id": "550e8400-e29b-41d4-a716-446655440000",
    "as_of_date": "2026-03-06",
    "mcsa_score": 82.5,
    "mcsa_band": "watchlist",
    "trend_score": 25.0,
    "vcp_component": 28.0,
    "volume_score": 12.0,
    "fundamental_score": 17.5,
    "evidence": {
        "trend": {"score": 25.0, "price_above_sma50": True},
        "vcp": {"score": 28.0, "pattern_detected": True},
        "volume": {"score": 12.0},
        "fundamentals": {"score": 17.5},
    },
    "missing_fields": [],
}

_SEED_RANGE = {
    "items": [
        {**_SEED_TICKER, "as_of_date": "2026-03-06", "mcsa_score": 82.5},
        {**_SEED_TICKER, "as_of_date": "2026-03-05", "mcsa_score": 80.0},
    ]
}


# ── Helpers ──────────────────────────────────────────────────────────

class _FakeScreenerClient:
    """Stub that returns deterministic data without touching the network."""

    def __init__(
        self,
        *,
        dashboard=_SEED_DASHBOARD,
        ticker=_SEED_TICKER,
        range_data=_SEED_RANGE,
    ):
        self._dashboard = dashboard
        self._ticker = ticker
        self._range = range_data

    def get_mcsa_latest_all(self, *, params=None):
        return self._dashboard

    def get_mcsa_latest_ticker(self, ticker):
        if self._ticker is None:
            return None
        return self._ticker

    def get_mcsa_range(self, *, ticker, from_date, to_date):
        return self._range


@pytest.fixture()
def _patch_client(monkeypatch):
    """Replace the lazy-singleton client with a fake."""
    import tayfin_bff.app as app_mod

    fake = _FakeScreenerClient()
    monkeypatch.setattr(app_mod, "_client_instance", fake)


@pytest.fixture()
def client(_patch_client):
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Tests ────────────────────────────────────────────────────────────


class TestMcsaDashboard:
    def test_returns_all_items(self, client):
        resp = client.get("/api/mcsa/dashboard")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body
        assert len(body["items"]) == 2

    def test_passes_band_filter_param(self, client, monkeypatch):
        """The BFF should forward query params to the ScreenerClient."""
        captured = {}

        class SpyClient(_FakeScreenerClient):
            def get_mcsa_latest_all(self, *, params=None):
                captured["params"] = params
                return _SEED_DASHBOARD

        import tayfin_bff.app as app_mod
        monkeypatch.setattr(app_mod, "_client_instance", SpyClient())

        client.get("/api/mcsa/dashboard?band=strong")
        assert captured["params"]["band"] == "strong"

    def test_upstream_none_returns_502(self, client, monkeypatch):
        import tayfin_bff.app as app_mod

        class DeadClient(_FakeScreenerClient):
            def get_mcsa_latest_all(self, *, params=None):
                return None

        monkeypatch.setattr(app_mod, "_client_instance", DeadClient())
        resp = client.get("/api/mcsa/dashboard")
        assert resp.status_code == 502


class TestMcsaTicker:
    def test_returns_ticker_data(self, client):
        resp = client.get("/api/mcsa/AAPL")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ticker"] == "AAPL"

    def test_ticker_not_found_returns_404(self, client, monkeypatch):
        import tayfin_bff.app as app_mod

        class NoDataClient(_FakeScreenerClient):
            def get_mcsa_latest_ticker(self, ticker):
                return None

        monkeypatch.setattr(app_mod, "_client_instance", NoDataClient())
        resp = client.get("/api/mcsa/ZZZZ")
        assert resp.status_code == 404

    def test_ticker_uppercased(self, client, monkeypatch):
        captured = {}

        class SpyClient(_FakeScreenerClient):
            def get_mcsa_latest_ticker(self, ticker):
                captured["ticker"] = ticker
                return _SEED_TICKER

        import tayfin_bff.app as app_mod
        monkeypatch.setattr(app_mod, "_client_instance", SpyClient())

        client.get("/api/mcsa/aapl")
        assert captured["ticker"] == "AAPL"


class TestMcsaRange:
    def test_returns_range_items(self, client):
        resp = client.get("/api/mcsa/range?ticker=AAPL&from=2026-03-01&to=2026-03-06")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body

    def test_missing_params_returns_400(self, client):
        resp = client.get("/api/mcsa/range?ticker=AAPL")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "missing_params"

    def test_upstream_none_returns_502(self, client, monkeypatch):
        import tayfin_bff.app as app_mod

        class DeadClient(_FakeScreenerClient):
            def get_mcsa_range(self, *, ticker, from_date, to_date):
                return None

        monkeypatch.setattr(app_mod, "_client_instance", DeadClient())
        resp = client.get("/api/mcsa/range?ticker=AAPL&from=2026-03-01&to=2026-03-06")
        assert resp.status_code == 502
