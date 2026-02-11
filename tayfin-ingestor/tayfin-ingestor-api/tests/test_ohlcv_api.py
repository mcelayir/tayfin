"""Integration tests for the unified GET /ohlcv endpoint.

Groups:
  A) /ohlcv latest-mode validation  (no from/to)
  B) /ohlcv range-mode validation   (with from/to)
  C) /ohlcv?ticker          — latest happy path
  D) /ohlcv?ticker&from&to  — range happy path
  E) /ohlcv?index_code      — latest-by-index happy path
  F) 404 cases
"""
from __future__ import annotations

import pytest

from conftest import AAPL_DATES, MSFT_DATES, TEST_INDEX_CODE

CANDLE_KEYS = {"ticker", "as_of_date", "open", "high", "low", "close", "volume", "source"}


# ================================================================
# A) /ohlcv/latest validation
# ================================================================


class TestOhlcvLatestModeValidation:
    """Validation rules for GET /ohlcv in latest mode (no from/to)."""

    def test_no_params_400(self, client):
        resp = client.get("/ohlcv")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"

    def test_ticker_and_index_code_400(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&index_code=NDX")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"


# ================================================================
# B) /ohlcv range validation
# ================================================================


class TestOhlcvRangeModeValidation:
    """Validation rules for GET /ohlcv in range mode (with from/to)."""

    def test_missing_ticker_400(self, client):
        resp = client.get("/ohlcv?from=2025-01-01")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"

    def test_ticker_and_index_code_400(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&index_code=NDX&from=2025-01-01")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"

    def test_invalid_date_format_400(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2025-13-01")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"

    def test_from_after_to_400(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2025-02-01&to=2025-01-01")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "invalid_request"


# ================================================================
# C) /ohlcv/latest?ticker — happy path
# ================================================================


class TestOhlcvLatestTicker:
    """Correct response for latest candle by ticker (no from/to)."""

    def test_status_200(self, client):
        resp = client.get("/ohlcv?ticker=AAPL")
        assert resp.status_code == 200

    def test_response_keys(self, client):
        resp = client.get("/ohlcv?ticker=AAPL")
        body = resp.get_json()
        assert CANDLE_KEYS == set(body.keys())

    def test_latest_date(self, client, seed):
        resp = client.get("/ohlcv?ticker=AAPL")
        body = resp.get_json()
        assert body["as_of_date"] == seed["aapl_latest"].isoformat()

    def test_types(self, client):
        body = client.get("/ohlcv?ticker=AAPL").get_json()
        assert isinstance(body["open"], (int, float))
        assert isinstance(body["high"], (int, float))
        assert isinstance(body["low"], (int, float))
        assert isinstance(body["close"], (int, float))
        assert isinstance(body["volume"], int)
        assert isinstance(body["ticker"], str)
        assert isinstance(body["source"], str)


# ================================================================
# D) /ohlcv?ticker range — happy path
# ================================================================


class TestOhlcvRange:
    """Correct response for date-range candle query."""

    def test_status_200(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-10&to=2099-01-12")
        assert resp.status_code == 200

    def test_items_count(self, client, seed):
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-10&to=2099-01-12")
        body = resp.get_json()
        expected = len([d for d in seed["aapl_dates"] if d.isoformat() >= "2099-01-10" and d.isoformat() <= "2099-01-12"])
        assert body["count"] == expected
        assert len(body["items"]) == expected

    def test_ascending_order(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-10&to=2099-01-12")
        body = resp.get_json()
        dates = [it["as_of_date"] for it in body["items"]]
        assert dates == sorted(dates)

    def test_envelope_keys(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-10&to=2099-01-12")
        body = resp.get_json()
        assert "ticker" in body
        assert "from" in body
        assert "to" in body
        assert "items" in body
        assert "count" in body

    def test_item_keys(self, client):
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-10&to=2099-01-12")
        body = resp.get_json()
        for item in body["items"]:
            assert CANDLE_KEYS == set(item.keys())

    def test_partial_range(self, client):
        """Only 'from' provided — returns rows from that date onwards."""
        resp = client.get("/ohlcv?ticker=AAPL&from=2099-01-11")
        body = resp.get_json()
        # Should include 2099-01-11, 2099-01-12 (2 rows)
        assert body["count"] == 2
        assert body["items"][0]["as_of_date"] == "2099-01-11"


# ================================================================
# E) /ohlcv/latest?index_code — happy path
# ================================================================


class TestOhlcvLatestIndex:
    """Correct response for latest candles by index code (no from/to)."""

    def test_status_200(self, client, seed):
        resp = client.get(f"/ohlcv?index_code={seed['index_code']}")
        assert resp.status_code == 200

    def test_response_shape(self, client, seed):
        body = client.get(f"/ohlcv?index_code={seed['index_code']}").get_json()
        assert "index_code" in body
        assert "items" in body
        assert "count" in body

    def test_items_length(self, client, seed):
        body = client.get(f"/ohlcv?index_code={seed['index_code']}").get_json()
        assert body["count"] == 2
        assert len(body["items"]) == 2

    def test_item_candle_keys(self, client, seed):
        body = client.get(f"/ohlcv?index_code={seed['index_code']}").get_json()
        for item in body["items"]:
            assert CANDLE_KEYS == set(item.keys())

    def test_per_ticker_latest_dates(self, client, seed):
        body = client.get(f"/ohlcv?index_code={seed['index_code']}").get_json()
        by_ticker = {it["ticker"]: it for it in body["items"]}
        assert by_ticker["AAPL"]["as_of_date"] == seed["aapl_latest"].isoformat()
        assert by_ticker["MSFT"]["as_of_date"] == seed["msft_latest"].isoformat()
        # Prove they differ
        assert seed["aapl_latest"] != seed["msft_latest"]

    def test_sorted_by_ticker(self, client, seed):
        body = client.get(f"/ohlcv?index_code={seed['index_code']}").get_json()
        tickers = [it["ticker"] for it in body["items"]]
        assert tickers == sorted(tickers)


# ================================================================
# F) 404 cases
# ================================================================


class TestOhlcvNotFound:
    """Endpoints return 404 for unknown instruments / indices."""

    def test_latest_unknown_ticker_404(self, client):
        resp = client.get("/ohlcv?ticker=ZZZUNKNOWN")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"] == "not_found"

    def test_range_unknown_ticker_404(self, client):
        resp = client.get("/ohlcv?ticker=ZZZUNKNOWN&from=2025-01-01&to=2025-12-31")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"] == "not_found"

    def test_latest_unknown_index_404(self, client):
        resp = client.get("/ohlcv?index_code=ZZZUNKNOWN")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["error"] == "not_found"
