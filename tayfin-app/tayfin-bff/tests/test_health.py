"""BFF health endpoint test."""

from __future__ import annotations

import pytest

from tayfin_bff.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body == {"status": "ok"}
