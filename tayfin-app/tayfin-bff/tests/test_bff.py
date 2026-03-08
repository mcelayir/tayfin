"""Smoke tests for the Tayfin BFF (HTMX dashboard).

Tests the Flask app factory, routes, and HTMX partials
using Flask's test client — no real screener API needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tayfin_bff.app import _build_rs_histogram, _sort_rows, create_app


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture()
def app():
    """Create a Flask test app with mocked ScreenerClient."""
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _sample_mcsa_rows() -> list[dict]:
    """Return sample MCSA result rows."""
    return [
        {
            "ticker": "AAPL",
            "instrument_id": "id-1",
            "as_of_date": "2026-03-08",
            "mcsa_pass": True,
            "rs_rank": 85.0,
            "criteria_count_pass": 8,
            "criteria_json": {
                "c_1": True, "c_2": True, "c_3": True, "c_4": True,
                "c_5": True, "c_6": True, "c_7": True, "c_8": True,
            },
        },
        {
            "ticker": "MSFT",
            "instrument_id": "id-2",
            "as_of_date": "2026-03-08",
            "mcsa_pass": False,
            "rs_rank": 45.0,
            "criteria_count_pass": 5,
            "criteria_json": {
                "c_1": True, "c_2": True, "c_3": True, "c_4": True,
                "c_5": True, "c_6": False, "c_7": False, "c_8": False,
            },
        },
    ]


# ===================================================================
# Pure helper tests
# ===================================================================


class TestBuildRsHistogram:
    def test_buckets_count(self):
        histogram = _build_rs_histogram(_sample_mcsa_rows())
        assert len(histogram) == 10

    def test_bucket_format(self):
        histogram = _build_rs_histogram(_sample_mcsa_rows())
        for b in histogram:
            assert "range" in b
            assert "count" in b
            assert "pct" in b

    def test_values_distributed(self):
        histogram = _build_rs_histogram(_sample_mcsa_rows())
        total = sum(b["count"] for b in histogram)
        assert total == 2  # 2 rows

    def test_empty_rows(self):
        histogram = _build_rs_histogram([])
        assert len(histogram) == 10
        assert all(b["count"] == 0 for b in histogram)


class TestSortRows:
    def test_sort_desc(self):
        rows = [{"rs_rank": 50}, {"rs_rank": 80}, {"rs_rank": 30}]
        _sort_rows(rows, "rs_rank", "desc")
        assert rows[0]["rs_rank"] == 80
        assert rows[-1]["rs_rank"] == 30

    def test_sort_asc(self):
        rows = [{"rs_rank": 50}, {"rs_rank": 80}, {"rs_rank": 30}]
        _sort_rows(rows, "rs_rank", "asc")
        assert rows[0]["rs_rank"] == 30
        assert rows[-1]["rs_rank"] == 80

    def test_none_values_pushed_to_end(self):
        rows = [{"rs_rank": None}, {"rs_rank": 80}, {"rs_rank": 30}]
        _sort_rows(rows, "rs_rank", "desc")
        assert rows[-1]["rs_rank"] is None


# ===================================================================
# Route tests
# ===================================================================


class TestHealthEndpoint:
    @patch("tayfin_bff.app.ScreenerClient")
    def test_health_ok(self, MockClient, client):
        mock = MockClient.return_value
        mock.health.return_value = True
        resp = client.get("/health")
        assert resp.status_code == 200

    @patch("tayfin_bff.app.ScreenerClient")
    def test_health_degraded(self, MockClient, client):
        mock = MockClient.return_value
        mock.health.return_value = False
        resp = client.get("/health")
        assert resp.status_code == 503


class TestMcsaDashboard:
    def test_returns_html(self, client):
        resp = client.get("/mcsa")
        assert resp.status_code == 200
        assert b"MCSA" in resp.data

    def test_contains_htmx_triggers(self, client):
        resp = client.get("/mcsa")
        assert b"hx-get" in resp.data
        assert b"htmx" in resp.data


class TestIndexRedirect:
    def test_redirects_to_mcsa(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/mcsa" in resp.headers["Location"]


class TestApiMcsaLatest:
    @patch("tayfin_bff.app.ScreenerClient")
    def test_returns_json(self, MockClient, client):
        mock = MockClient.return_value
        mock.get_mcsa_latest.return_value = _sample_mcsa_rows()
        resp = client.get("/api/mcsa/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert len(data["items"]) == 2


class TestApiRsHistogram:
    @patch("tayfin_bff.app.ScreenerClient")
    def test_returns_buckets(self, MockClient, client):
        mock = MockClient.return_value
        mock.get_mcsa_latest.return_value = _sample_mcsa_rows()
        resp = client.get("/api/mcsa/rs-histogram")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "buckets" in data
        assert len(data["buckets"]) == 10
