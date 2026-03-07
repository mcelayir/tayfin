"""MCSA API endpoint tests — Flask test client with monkeypatched repository.

No real DB, no real network.
"""

from __future__ import annotations

from datetime import date

import pytest

# ── Deterministic fake data ──────────────────────────────────────────

_SEED_MCSA_ROW = {
    "ticker": "AAPL",
    "instrument_id": "550e8400-e29b-41d4-a716-446655440000",
    "as_of_date": date(2026, 3, 6),
    "mcsa_score": 82.5,
    "mcsa_band": "watchlist",
    "trend_score": 25.0,
    "vcp_component": 28.0,
    "volume_score": 12.0,
    "fundamental_score": 17.5,
    "evidence_json": {
        "trend": {"score": 25.0, "price_above_sma50": True},
        "vcp": {"score": 28.0, "pattern_detected": True},
        "volume": {"score": 12.0},
        "fundamentals": {"score": 17.5},
    },
    "missing_fields": [],
}

_ALL_MCSA_ROWS = [
    _SEED_MCSA_ROW,
    {
        "ticker": "MSFT",
        "instrument_id": None,
        "as_of_date": date(2026, 3, 6),
        "mcsa_score": 45.0,
        "mcsa_band": "weak",
        "trend_score": 10.0,
        "vcp_component": 15.0,
        "volume_score": 5.0,
        "fundamental_score": 15.0,
        "evidence_json": {"trend": {"score": 10.0}},
        "missing_fields": ["vcp.vcp_score"],
    },
]

_RANGE_MCSA_ROWS = [
    {**_SEED_MCSA_ROW, "as_of_date": date(2026, 3, 6), "mcsa_score": 82.5},
    {**_SEED_MCSA_ROW, "as_of_date": date(2026, 3, 5), "mcsa_score": 80.0},
    {**_SEED_MCSA_ROW, "as_of_date": date(2026, 3, 4), "mcsa_score": 78.0},
]


# ── Helpers ──────────────────────────────────────────────────────────


def _patch_mcsa_repo(
    monkeypatch,
    *,
    latest=_SEED_MCSA_ROW,
    all_rows=_ALL_MCSA_ROWS,
    range_rows=_RANGE_MCSA_ROWS,
):
    """Monkeypatch MCSA + VCP repository functions + get_engine."""
    # VCP stubs (needed because app imports them at module level)
    monkeypatch.setattr("tayfin_screener_api.app.ping_db", lambda engine: True)
    monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake-engine")
    monkeypatch.setattr(
        "tayfin_screener_api.app.vcp_get_latest_by_ticker",
        lambda engine, ticker: None,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.vcp_get_latest_all",
        lambda engine, **kw: [],
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.vcp_get_range_by_ticker",
        lambda engine, ticker, from_date, to_date: [],
    )
    # MCSA stubs
    monkeypatch.setattr(
        "tayfin_screener_api.app.mcsa_get_latest_by_ticker",
        lambda engine, ticker: latest if latest and latest["ticker"] == ticker else None,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.mcsa_get_latest_all",
        lambda engine, **kw: all_rows,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.mcsa_get_range_by_ticker",
        lambda engine, ticker, from_date, to_date: range_rows,
    )


@pytest.fixture
def mcsa_client(monkeypatch):
    """Flask test client with MCSA repository functions monkeypatched."""
    _patch_mcsa_repo(monkeypatch)
    from tayfin_screener_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mcsa_client_empty(monkeypatch):
    """Flask test client where MCSA queries return empty / None."""
    _patch_mcsa_repo(monkeypatch, latest=None, all_rows=[], range_rows=[])
    from tayfin_screener_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# =====================================================================
# GET /mcsa/latest/<ticker>
# =====================================================================


class TestMcsaLatestTicker:
    def test_found(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest/AAPL")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["mcsa_score"] == 82.5
        assert data["mcsa_band"] == "watchlist"
        assert data["trend_score"] == 25.0
        assert data["vcp_component"] == 28.0
        assert data["volume_score"] == 12.0
        assert data["fundamental_score"] == 17.5
        assert "evidence" in data
        assert "missing_fields" in data

    def test_not_found(self, mcsa_client_empty):
        resp = mcsa_client_empty.get("/mcsa/latest/AAPL")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not_found"

    def test_ticker_uppercased(self, monkeypatch):
        """Lowercase ticker in URL should be uppercased."""
        captured = {}

        def fake_get(engine, ticker):
            captured["ticker"] = ticker
            return {**_SEED_MCSA_ROW, "ticker": ticker}

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.mcsa_get_latest_by_ticker", fake_get)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/mcsa/latest/aapl")
        assert captured["ticker"] == "AAPL"

    def test_instrument_id_serialised(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest/AAPL")
        data = resp.get_json()
        assert data["instrument_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_null_instrument_id(self, monkeypatch):
        row = {**_SEED_MCSA_ROW, "instrument_id": None, "ticker": "X"}
        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr(
            "tayfin_screener_api.app.mcsa_get_latest_by_ticker",
            lambda engine, ticker: row if ticker == "X" else None,
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            data = c.get("/mcsa/latest/X").get_json()
        assert data["instrument_id"] is None

    def test_evidence_json_string_parsed(self, monkeypatch):
        """evidence_json stored as a string should be parsed to dict."""
        import json
        row = {**_SEED_MCSA_ROW, "evidence_json": json.dumps({"a": 1})}
        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr(
            "tayfin_screener_api.app.mcsa_get_latest_by_ticker",
            lambda engine, ticker: row,
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            data = c.get("/mcsa/latest/AAPL").get_json()
        assert data["evidence"] == {"a": 1}

    def test_missing_fields_string_parsed(self, monkeypatch):
        """missing_fields stored as a string should be parsed to list."""
        import json
        row = {**_SEED_MCSA_ROW, "missing_fields": json.dumps(["trend.sma_50"])}
        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr(
            "tayfin_screener_api.app.mcsa_get_latest_by_ticker",
            lambda engine, ticker: row,
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            data = c.get("/mcsa/latest/AAPL").get_json()
        assert data["missing_fields"] == ["trend.sma_50"]


# =====================================================================
# GET /mcsa/latest
# =====================================================================


class TestMcsaLatestAll:
    def test_returns_items(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert len(data["items"]) == 2

    def test_empty(self, mcsa_client_empty):
        resp = mcsa_client_empty.get("/mcsa/latest")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_band_param(self, monkeypatch):
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.mcsa_get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/mcsa/latest?band=strong")
        assert captured["band"] == "strong"

    def test_bad_band_param(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest?band=invalid")
        assert resp.status_code == 400

    def test_min_score_param(self, monkeypatch):
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.mcsa_get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/mcsa/latest?min_score=60")
        assert captured["min_score"] == 60.0

    def test_bad_min_score(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest?min_score=abc")
        assert resp.status_code == 400

    def test_bad_limit(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest?limit=abc")
        assert resp.status_code == 400

    def test_limit_capped(self, monkeypatch):
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.mcsa_get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/mcsa/latest?limit=9999")
        assert captured["limit"] == 1000  # capped at _MAX_LIMIT

    def test_items_serialised_correctly(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/latest")
        data = resp.get_json()
        item = data["items"][0]
        assert "ticker" in item
        assert "mcsa_score" in item
        assert "mcsa_band" in item
        assert "as_of_date" in item
        assert "trend_score" in item
        assert "evidence" in item


# =====================================================================
# GET /mcsa/range
# =====================================================================


class TestMcsaRange:
    def test_success(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["from"] == "2026-03-01"
        assert data["to"] == "2026-03-07"
        assert len(data["items"]) == 3

    def test_missing_ticker(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_params"

    def test_missing_from(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&to=2026-03-07")
        assert resp.status_code == 400

    def test_missing_to(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&from=2026-03-01")
        assert resp.status_code == 400

    def test_bad_date_format(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&from=03-01-2026&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_date"

    def test_from_after_to(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&from=2026-03-10&to=2026-03-01")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_range"

    def test_range_too_large(self, mcsa_client):
        resp = mcsa_client.get("/mcsa/range?ticker=AAPL&from=2015-01-01&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "range_too_large"

    def test_empty_range(self, mcsa_client_empty):
        resp = mcsa_client_empty.get("/mcsa/range?ticker=AAPL&from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_ticker_uppercased(self, monkeypatch):
        captured = {}

        def fake_range(engine, ticker, from_date, to_date):
            captured["ticker"] = ticker
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.mcsa_get_range_by_ticker", fake_range)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/mcsa/range?ticker=aapl&from=2026-03-01&to=2026-03-07")
        assert captured["ticker"] == "AAPL"
