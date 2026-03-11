import json

import pytest

from tayfin_ingestor_api.app import create_app


class DummyRepo:
    def __init__(self, engine=None, *, latest=None, snapshots=None):
        self._latest = latest
        self._snapshots = snapshots or []

    def resolve_instrument(self, ticker: str, country: str):
        if ticker == "FOUND":
            return {"id": "inst-1", "ticker": ticker, "country": country}
        return None

    def get_latest_snapshot(self, instrument_id: str):
        return self._latest

    def get_snapshots_range(self, instrument_id: str, fr, to, limit: int, order: str):
        return self._snapshots


@pytest.fixture
def app(monkeypatch):
    app = create_app()

    # Patch the repository used by handlers to a dummy implementation
    from tayfin_ingestor_api import app as app_module

    def make_repo(engine):
        # provide a sensible latest snapshot and a couple of range items
        latest = {
            "as_of_date": __import__("datetime").date(2026, 3, 11),
            "metrics": {
                "revenue_growth_yoy": -0.47,
                "earnings_growth_yoy": -98.57,
                "roe": 0.19,
                "net_margin": 0.36,
                "debt_equity": 0.50,
            },
        }
        snapshots = [
            {"as_of_date": "2026-03-10", "price": 48.0},
            {"as_of_date": "2026-03-11", "price": 48.27},
        ]
        return DummyRepo(engine, latest=latest, snapshots=snapshots)

    monkeypatch.setattr(app_module, "FundamentalsRepository", lambda engine: make_repo(engine))
    yield app


def test_latest_returns_snapshot(app):
    client = app.test_client()
    resp = client.get("/fundamentals/latest?symbol=FOUND&country=US")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["symbol"] == "FOUND"
    assert body["as_of_date"] == "2026-03-11"
    assert "revenue_growth_yoy" in body


def test_latest_returns_404_for_unknown(app):
    client = app.test_client()
    resp = client.get("/fundamentals/latest?symbol=NOPE&country=US")
    assert resp.status_code == 404


def test_range_returns_items(app):
    client = app.test_client()
    resp = client.get("/fundamentals?symbol=FOUND&country=US&from=2026-03-09&to=2026-03-12&limit=10")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["symbol"] == "FOUND"
    assert body["count"] == 2
    assert isinstance(body["items"], list)
