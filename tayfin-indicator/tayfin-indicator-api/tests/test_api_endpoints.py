"""API endpoint tests — Flask test client with monkeypatched repository.

No real DB, no real network.
"""

from __future__ import annotations

from datetime import date

import pytest

# ── Deterministic fake data ──────────────────────────────────────────

_SEED_ROW = {
    "ticker": "AAPL",
    "as_of_date": date(2026, 2, 12),
    "indicator_key": "sma",
    "params_json": '{"window": 50}',
    "value": 268.081,
    "source": "computed",
}

_RANGE_ROWS = [
    {"as_of_date": date(2025, 3, 5), "value": 239.3636},
    {"as_of_date": date(2025, 3, 6), "value": 239.0744},
    {"as_of_date": date(2025, 3, 7), "value": 238.766},
]

_INDEX_ROWS = [
    {"ticker": "AAPL", "as_of_date": date(2026, 2, 12), "value": 268.081},
    {"ticker": "MSFT", "as_of_date": date(2026, 2, 12), "value": 399.55},
]


# ── Helpers ──────────────────────────────────────────────────────────


def _patch_repo(monkeypatch, *, latest=_SEED_ROW, range_rows=_RANGE_ROWS, index_rows=_INDEX_ROWS):
    """Monkeypatch all three repository functions + ping_db + get_engine."""

    monkeypatch.setattr(
        "tayfin_indicator_api.app.ping_db",
        lambda engine: True,
    )
    monkeypatch.setattr(
        "tayfin_indicator_api.app.get_engine",
        lambda: "fake-engine",
    )
    monkeypatch.setattr(
        "tayfin_indicator_api.app.get_latest",
        lambda engine, ticker, indicator_key, params_json=None: latest,
    )
    monkeypatch.setattr(
        "tayfin_indicator_api.app.get_range",
        lambda engine, ticker, indicator_key, from_date, to_date, params_json=None: range_rows,
    )
    monkeypatch.setattr(
        "tayfin_indicator_api.app.get_index_latest",
        lambda engine, indicator_key, params_json=None: index_rows,
    )


@pytest.fixture
def client(monkeypatch):
    """Flask test client with all repository functions monkeypatched."""
    _patch_repo(monkeypatch)

    from tayfin_indicator_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_empty(monkeypatch):
    """Flask test client where get_latest returns None (not found)."""
    _patch_repo(monkeypatch, latest=None, range_rows=[], index_rows=[])

    from tayfin_indicator_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Health ───────────────────────────────────────────────────────────


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


# ── /indicators/latest ───────────────────────────────────────────────


class TestIndicatorsLatest:
    def test_returns_200_and_correct_shape(self, client):
        resp = client.get("/indicators/latest?ticker=AAPL&indicator=sma&window=50")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["indicator"] == "sma"
        assert data["value"] == pytest.approx(268.081)
        assert "as_of_date" in data
        assert "source" in data
        assert "params" in data

    def test_missing_ticker_returns_400(self, client):
        resp = client.get("/indicators/latest?indicator=sma")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_params"

    def test_missing_indicator_returns_400(self, client):
        resp = client.get("/indicators/latest?ticker=AAPL")
        assert resp.status_code == 400

    def test_not_found_returns_404(self, client_empty):
        resp = client_empty.get("/indicators/latest?ticker=ZZZ&indicator=sma")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not_found"


# ── /indicators/range ────────────────────────────────────────────────


class TestIndicatorsRange:
    def test_returns_200_with_items(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma&window=50"
            "&from=2025-01-01&to=2026-02-12"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["indicator"] == "sma"
        assert len(data["items"]) == 3
        assert "as_of_date" in data["items"][0]
        assert "value" in data["items"][0]

    def test_missing_from_returns_400(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma&to=2026-02-12"
        )
        assert resp.status_code == 400

    def test_missing_to_returns_400(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma&from=2025-01-01"
        )
        assert resp.status_code == 400

    def test_bad_date_format_returns_400(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma"
            "&from=2025-13-01&to=2026-02-12"
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_date"

    def test_from_after_to_returns_400(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma"
            "&from=2027-01-01&to=2026-01-01"
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_range"

    def test_range_too_large_returns_400(self, client):
        resp = client.get(
            "/indicators/range?ticker=AAPL&indicator=sma"
            "&from=2015-01-01&to=2026-02-12"
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "range_too_large"

    def test_empty_range_returns_200(self, client_empty):
        resp = client_empty.get(
            "/indicators/range?ticker=AAPL&indicator=sma"
            "&from=2025-01-01&to=2025-02-01"
        )
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []


# ── /indicators/index/latest ────────────────────────────────────────


class TestIndicatorsIndexLatest:
    def test_returns_200_with_list(self, client):
        resp = client.get(
            "/indicators/index/latest?index_code=NDX&indicator=sma&window=50"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["index_code"] == "NDX"
        assert data["indicator"] == "sma"
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 2
        tickers = [i["ticker"] for i in data["items"]]
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_missing_index_code_returns_400(self, client):
        resp = client.get("/indicators/index/latest?indicator=sma")
        assert resp.status_code == 400

    def test_missing_indicator_returns_400(self, client):
        resp = client.get("/indicators/index/latest?index_code=NDX")
        assert resp.status_code == 400

    def test_empty_index_returns_200(self, client_empty):
        resp = client_empty.get(
            "/indicators/index/latest?index_code=NDX&indicator=sma"
        )
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []
