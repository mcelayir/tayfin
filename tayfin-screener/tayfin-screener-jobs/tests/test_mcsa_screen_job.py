"""Smoke tests for the MCSA screen job orchestration.

Uses mocked dependencies — no DB, no network.
Follows the same pattern as test_vcp_screen_job.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from tayfin_screener_jobs.jobs.mcsa_screen_job import McsaScreenJob, _compute_return


# ===================================================================
# Fixtures & helpers
# ===================================================================

_SAMPLE_UUID = uuid4()


def _make_ohlcv_rows(n: int = 30, base_close: float = 100.0) -> list[dict]:
    """Return *n* synthetic OHLCV rows with ascending dates."""
    base = date.today() - timedelta(days=n)
    return [
        {
            "as_of_date": (base + timedelta(days=i)).isoformat(),
            "open": base_close + i,
            "high": base_close + i + 5,
            "low": base_close + i - 5,
            "close": base_close + i,
            "volume": 1_000_000,
        }
        for i in range(n)
    ]


def _make_index_latest(tickers: list[str], value: float = 150.0) -> list[dict]:
    """Return bulk indicator response for a list of tickers."""
    return [
        {"ticker": t, "as_of_date": date.today().isoformat(), "value": value}
        for t in tickers
    ]


def _make_range_items(n: int = 10, value: float = 150.0) -> list[dict]:
    """Return indicator range response."""
    return [
        {
            "as_of_date": (date.today() - timedelta(days=n - i)).isoformat(),
            "value": value + i * 0.1,
        }
        for i in range(n)
    ]


def _mock_repos():
    job_run_repo = MagicMock()
    job_run_repo.create.return_value = _SAMPLE_UUID

    job_run_item_repo = MagicMock()
    mcsa_result_repo = MagicMock()

    return job_run_repo, job_run_item_repo, mcsa_result_repo


def _build_job(
    *,
    ingestor=None,
    indicator=None,
    tickers=None,
) -> McsaScreenJob:
    """Build an McsaScreenJob with mocked dependencies."""
    jr, jri, mcsa = _mock_repos()
    _tickers = tickers or ["AAPL", "MSFT"]

    _ingestor = ingestor or MagicMock()
    _ingestor.get_index_members.return_value = [
        {"symbol": t, "instrument_id": f"id-{t}"} for t in _tickers
    ]
    # Default: return valid OHLCV for RS calculation
    _ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(130)

    _indicator = indicator or MagicMock()
    # Default: return valid bulk indicator responses
    _indicator.get_index_latest.return_value = _make_index_latest(_tickers)
    _indicator.get_range.return_value = _make_range_items(10)

    return McsaScreenJob(
        target_name="test-target",
        target_cfg={"index_code": "NDX", "country": "US"},
        full_cfg={},
        engine=MagicMock(),
        ingestor_client=_ingestor,
        indicator_client=_indicator,
        job_run_repo=jr,
        job_run_item_repo=jri,
        mcsa_result_repo=mcsa,
    )


# ===================================================================
# Test _compute_return
# ===================================================================


class TestComputeReturn:
    """Tests for :func:`_compute_return`."""

    def test_positive_return(self):
        rows = [
            {"as_of_date": "2026-01-01", "close": 100},
            {"as_of_date": "2026-06-01", "close": 150},
        ]
        assert _compute_return(rows) == pytest.approx(0.5)

    def test_negative_return(self):
        rows = [
            {"as_of_date": "2026-01-01", "close": 100},
            {"as_of_date": "2026-06-01", "close": 80},
        ]
        assert _compute_return(rows) == pytest.approx(-0.2)

    def test_empty_rows(self):
        assert _compute_return([]) == 0.0

    def test_single_row(self):
        assert _compute_return([{"as_of_date": "2026-01-01", "close": 100}]) == 0.0

    def test_zero_earliest(self):
        rows = [
            {"as_of_date": "2026-01-01", "close": 0},
            {"as_of_date": "2026-06-01", "close": 100},
        ]
        assert _compute_return(rows) == 0.0


# ===================================================================
# Test McsaScreenJob.from_config
# ===================================================================


class TestFromConfig:
    def test_returns_instance(self):
        from unittest.mock import patch

        with patch("tayfin_screener_jobs.jobs.mcsa_screen_job.get_engine") as mock:
            mock.return_value = MagicMock()
            job = McsaScreenJob.from_config(
                target_name="nasdaq-100",
                target_cfg={"index_code": "NDX", "country": "US"},
                full_cfg={},
            )
            assert isinstance(job, McsaScreenJob)
            assert job.target_name == "nasdaq-100"


# ===================================================================
# Test McsaScreenJob.run orchestration
# ===================================================================


class TestRunOrchestration:
    def test_creates_and_finalises_job_run(self):
        job = _build_job()
        job.run()

        job.job_run_repo.create.assert_called_once()
        job.job_run_repo.finalize.assert_called_once()

    def test_success_when_all_tickers_pass(self):
        job = _build_job()
        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["status"] == "SUCCESS"
        assert call_kwargs.kwargs["items_succeeded"] == 2
        assert call_kwargs.kwargs["items_failed"] == 0

    def test_bulk_indicator_calls(self):
        """Verifies 6 bulk calls, not N per-ticker calls (ARCH_BLOCKER)."""
        job = _build_job()
        job.run()

        # 6 bulk indicator calls: sma_50, sma_150, sma_200,
        # rolling_high_252, rolling_low_252, sma_slope_200
        assert job.indicator.get_index_latest.call_count == 6

    def test_single_ticker_override(self):
        job = _build_job(tickers=["GOOG"])
        # Ensure bulk indicators include GOOG
        job.indicator.get_index_latest.return_value = _make_index_latest(["GOOG"])
        job.run(ticker="GOOG")

        job.ingestor.get_index_members.assert_not_called()
        assert job.mcsa_result_repo.upsert.call_count == 1

    def test_limit_caps_tickers(self):
        job = _build_job(tickers=[f"S{i}" for i in range(10)])
        job.run(limit=3)

        assert job.mcsa_result_repo.upsert.call_count == 3

    def test_continues_on_ticker_failure(self):
        job = _build_job()
        # Make indicator return empty for first ticker so it fails
        side_effects = [
            _make_index_latest(["MSFT"]),  # sma_50 — missing AAPL → will fail
        ] * 6
        job.indicator.get_index_latest.side_effect = side_effects

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        # At least one should fail, at least one succeed
        total = (
            call_kwargs.kwargs["items_succeeded"]
            + call_kwargs.kwargs["items_failed"]
        )
        assert total == 2

    def test_upsert_called_per_success(self):
        job = _build_job()
        job.run()

        # Should upsert once per successful ticker
        assert job.mcsa_result_repo.upsert.call_count == 2

    def test_job_run_item_created_per_ticker(self):
        job = _build_job()
        job.run()

        assert job.job_run_item_repo.create.call_count == 2


# ===================================================================
# Test RS computation helper
# ===================================================================


class TestFetchBulkIndicators:
    def test_returns_nested_dict(self):
        job = _build_job()
        data = job._fetch_bulk_indicators("NDX")

        assert "sma_50" in data
        assert "sma_150" in data
        assert "sma_200" in data
        assert "rolling_high_252" in data
        assert "rolling_low_252" in data
        assert "sma_slope_200" in data

    def test_values_are_floats(self):
        job = _build_job()
        data = job._fetch_bulk_indicators("NDX")

        for canon, ticker_map in data.items():
            for tkr, val in ticker_map.items():
                assert isinstance(val, float), f"{canon}/{tkr} is not float"
