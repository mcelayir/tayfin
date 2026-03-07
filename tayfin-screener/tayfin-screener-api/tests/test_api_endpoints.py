"""API endpoint tests — Flask test client with monkeypatched repository.

No real DB, no real network.
"""

from __future__ import annotations

from datetime import date

import pytest

# ── Deterministic fake data ──────────────────────────────────────────

_SEED_ROW = {
    "ticker": "AAPL",
    "instrument_id": "550e8400-e29b-41d4-a716-446655440000",
    "as_of_date": date(2026, 3, 6),
    "vcp_score": 72.0,
    "vcp_confidence": "high",
    "pattern_detected": True,
    "features_json": {
        "contraction": {"count": 3, "is_tightening": True, "total_decline": 0.18},
        "volatility": {"atr_trend": -0.12, "ma_alignment": True},
        "volume": {"volume_dryup": True, "volume_trend": -0.15},
        "breakdown": {"contraction": 32.0, "trend": 25.0, "volume": 15.0},
    },
}

_ALL_ROWS = [
    _SEED_ROW,
    {
        "ticker": "MSFT",
        "instrument_id": None,
        "as_of_date": date(2026, 3, 6),
        "vcp_score": 45.0,
        "vcp_confidence": "low",
        "pattern_detected": False,
        "features_json": {"contraction": {"count": 1}},
    },
]

_RANGE_ROWS = [
    {**_SEED_ROW, "as_of_date": date(2026, 3, 6), "vcp_score": 72.0},
    {**_SEED_ROW, "as_of_date": date(2026, 3, 5), "vcp_score": 68.0},
    {**_SEED_ROW, "as_of_date": date(2026, 3, 4), "vcp_score": 65.0},
]


# ── Helpers ──────────────────────────────────────────────────────────


def _patch_repo(
    monkeypatch,
    *,
    latest=_SEED_ROW,
    all_rows=_ALL_ROWS,
    range_rows=_RANGE_ROWS,
):
    """Monkeypatch all repository functions + get_engine."""
    monkeypatch.setattr(
        "tayfin_screener_api.app.ping_db",
        lambda engine: True,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.get_engine",
        lambda: "fake-engine",
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.get_latest_by_ticker",
        lambda engine, ticker: latest if latest and latest["ticker"] == ticker else None,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.get_latest_all",
        lambda engine, **kw: all_rows,
    )
    monkeypatch.setattr(
        "tayfin_screener_api.app.get_range_by_ticker",
        lambda engine, ticker, from_date, to_date: range_rows,
    )


@pytest.fixture
def client(monkeypatch):
    """Flask test client with all repository functions monkeypatched."""
    _patch_repo(monkeypatch)
    from tayfin_screener_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def client_empty(monkeypatch):
    """Flask test client where queries return empty / None."""
    _patch_repo(monkeypatch, latest=None, all_rows=[], range_rows=[])
    from tayfin_screener_api.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# =====================================================================
# Health
# =====================================================================


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_health_db_fail(self, monkeypatch):
        monkeypatch.setattr(
            "tayfin_screener_api.app.ping_db", lambda engine: False,
        )
        monkeypatch.setattr(
            "tayfin_screener_api.app.get_engine", lambda: "fake",
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            resp = c.get("/health")
            assert resp.status_code == 500


# =====================================================================
# GET /vcp/latest/<ticker>
# =====================================================================


class TestVcpLatestTicker:
    def test_found(self, client):
        resp = client.get("/vcp/latest/AAPL")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["vcp_score"] == 72.0
        assert data["pattern_detected"] is True
        assert data["vcp_confidence"] == "high"
        assert "features_json" in data

    def test_not_found(self, client_empty):
        resp = client_empty.get("/vcp/latest/AAPL")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not_found"

    def test_ticker_uppercased(self, monkeypatch):
        """Lowercase ticker in URL should be uppercased."""
        captured = {}

        def fake_get(engine, ticker):
            captured["ticker"] = ticker
            return {**_SEED_ROW, "ticker": ticker}

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.get_latest_by_ticker", fake_get)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/vcp/latest/aapl")
        assert captured["ticker"] == "AAPL"

    def test_instrument_id_serialised(self, client):
        resp = client.get("/vcp/latest/AAPL")
        data = resp.get_json()
        assert data["instrument_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_null_instrument_id(self, monkeypatch):
        row = {**_SEED_ROW, "instrument_id": None, "ticker": "X"}
        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr(
            "tayfin_screener_api.app.get_latest_by_ticker",
            lambda engine, ticker: row if ticker == "X" else None,
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            data = c.get("/vcp/latest/X").get_json()
        assert data["instrument_id"] is None

    def test_features_json_string_parsed(self, monkeypatch):
        """features_json stored as a string should be parsed to dict."""
        import json
        row = {**_SEED_ROW, "features_json": json.dumps({"a": 1})}
        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr(
            "tayfin_screener_api.app.get_latest_by_ticker",
            lambda engine, ticker: row,
        )
        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            data = c.get("/vcp/latest/AAPL").get_json()
        assert data["features_json"] == {"a": 1}


# =====================================================================
# GET /vcp/latest
# =====================================================================


class TestVcpLatestAll:
    def test_returns_items(self, client):
        resp = client.get("/vcp/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert len(data["items"]) == 2

    def test_empty(self, client_empty):
        resp = client_empty.get("/vcp/latest")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_pattern_only_param(self, monkeypatch):
        """pattern_only=true should be forwarded to the repository."""
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/vcp/latest?pattern_only=true")
        assert captured["pattern_only"] is True

    def test_min_score_param(self, monkeypatch):
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/vcp/latest?min_score=60")
        assert captured["min_score"] == 60.0

    def test_bad_min_score(self, client):
        resp = client.get("/vcp/latest?min_score=abc")
        assert resp.status_code == 400

    def test_bad_limit(self, client):
        resp = client.get("/vcp/latest?limit=abc")
        assert resp.status_code == 400

    def test_limit_capped(self, monkeypatch):
        captured = {}

        def fake_all(engine, **kw):
            captured.update(kw)
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.get_latest_all", fake_all)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/vcp/latest?limit=9999")
        assert captured["limit"] == 1000  # capped at _MAX_LIMIT

    def test_items_serialised_correctly(self, client):
        resp = client.get("/vcp/latest")
        data = resp.get_json()
        item = data["items"][0]
        assert "ticker" in item
        assert "vcp_score" in item
        assert "as_of_date" in item


# =====================================================================
# GET /vcp/range
# =====================================================================


class TestVcpRange:
    def test_success(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert data["from"] == "2026-03-01"
        assert data["to"] == "2026-03-07"
        assert len(data["items"]) == 3

    def test_missing_ticker(self, client):
        resp = client.get("/vcp/range?from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_params"

    def test_missing_from(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&to=2026-03-07")
        assert resp.status_code == 400

    def test_missing_to(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&from=2026-03-01")
        assert resp.status_code == 400

    def test_bad_date_format(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&from=03-01-2026&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_date"

    def test_from_after_to(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&from=2026-03-10&to=2026-03-01")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_range"

    def test_range_too_large(self, client):
        resp = client.get("/vcp/range?ticker=AAPL&from=2015-01-01&to=2026-03-07")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "range_too_large"

    def test_empty_range(self, client_empty):
        resp = client_empty.get("/vcp/range?ticker=AAPL&from=2026-03-01&to=2026-03-07")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_ticker_uppercased(self, monkeypatch):
        captured = {}

        def fake_range(engine, ticker, from_date, to_date):
            captured["ticker"] = ticker
            return []

        monkeypatch.setattr("tayfin_screener_api.app.get_engine", lambda: "fake")
        monkeypatch.setattr("tayfin_screener_api.app.get_range_by_ticker", fake_range)

        from tayfin_screener_api.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            c.get("/vcp/range?ticker=aapl&from=2026-03-01&to=2026-03-07")
        assert captured["ticker"] == "AAPL"
