"""Tests for tayfin_screener_jobs.jobs.mcsa_screen_job."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tayfin_screener_jobs.jobs.mcsa_screen_job import McsaScreenJob


# ===================================================================
# Fixtures & helpers
# ===================================================================

_SAMPLE_UUID = uuid4()


def _make_ohlcv_rows(n: int = 30) -> list[dict]:
    base = date.today() - timedelta(days=n)
    rows = []
    for i in range(n):
        d = (base + timedelta(days=i)).isoformat()
        rows.append({
            "as_of_date": d,
            "open": 100 + i,
            "high": 105 + i,
            "low": 95 + i,
            "close": 102 + i,
            "volume": 1_000_000 + i * 10_000,
        })
    return rows


def _make_indicator_latest(value: float = 100.0) -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": date.today().isoformat(),
        "indicator": "sma",
        "params": {"window": 50},
        "value": value,
        "source": "test",
    }


def _target_cfg() -> dict:
    """MCSA target config with required keys."""
    return {
        "index_code": "NDX",
        "country": "US",
        "lookback_days": 365,
        "indicators": [
            {"key": "sma", "window": 50},
            {"key": "sma", "window": 150},
            {"key": "sma", "window": 200},
            {"key": "rolling_high", "window": 252},
            {"key": "vol_sma", "window": 50},
        ],
        "mcsa": {
            "weights": {"trend": 30, "vcp": 35, "volume": 15, "fundamentals": 20},
        },
    }


def _mock_repos():
    """Return mocked repo instances."""
    job_run_repo = MagicMock()
    job_run_repo.create.return_value = _SAMPLE_UUID

    job_run_item_repo = MagicMock()
    job_run_item_repo.create.return_value = uuid4()

    mcsa_result_repo = MagicMock()
    mcsa_result_repo.upsert.return_value = 1

    vcp_read_repo = MagicMock()
    vcp_read_repo.get_latest_by_ticker.return_value = {
        "vcp_score": 75.0,
        "pattern_detected": True,
    }

    return job_run_repo, job_run_item_repo, mcsa_result_repo, vcp_read_repo


def _build_job(
    *,
    ingestor=None,
    indicator=None,
    target_cfg=None,
) -> McsaScreenJob:
    """Build an McsaScreenJob with fully mocked dependencies."""
    jr, jri, mcsa_repo, vcp_repo = _mock_repos()

    _ingestor = ingestor or MagicMock()
    _indicator = indicator or MagicMock()

    job = McsaScreenJob(
        target_name="test-target",
        target_cfg=target_cfg or _target_cfg(),
        full_cfg={"jobs": {"mcsa_screen": {"targets": {"test-target": _target_cfg()}}}},
        engine=MagicMock(),
        ingestor_client=_ingestor,
        indicator_client=_indicator,
        job_run_repo=jr,
        job_run_item_repo=jri,
        mcsa_result_repo=mcsa_repo,
        vcp_read_repo=vcp_repo,
    )
    return job


def _setup_clients():
    """Build ingestor + indicator mocks that return valid data."""
    ingestor = MagicMock()
    ingestor.get_index_members.return_value = [
        {"symbol": "AAPL", "instrument_id": "id-1"},
        {"symbol": "MSFT", "instrument_id": "id-2"},
    ]
    ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)
    ingestor.get_fundamentals_latest.return_value = {
        "revenue_growth_yoy": 0.25,
        "earnings_growth_yoy": 0.30,
        "roe": 0.20,
        "net_margin": 0.12,
        "debt_equity": 0.6,
    }

    indicator = MagicMock()
    indicator.get_latest.return_value = _make_indicator_latest(150.0)

    return ingestor, indicator


# ===================================================================
# TestFromConfig
# ===================================================================

class TestFromConfig:

    @patch("tayfin_screener_jobs.jobs.mcsa_screen_job.get_engine")
    def test_returns_instance(self, mock_engine):
        mock_engine.return_value = MagicMock()
        job = McsaScreenJob.from_config(
            target_name="nasdaq-100",
            target_cfg=_target_cfg(),
            full_cfg={},
        )
        assert isinstance(job, McsaScreenJob)
        assert job.target_name == "nasdaq-100"

    @patch("tayfin_screener_jobs.jobs.mcsa_screen_job.get_engine")
    def test_stores_config(self, mock_engine):
        mock_engine.return_value = MagicMock()
        cfg = _target_cfg()
        job = McsaScreenJob.from_config(
            target_name="t", target_cfg=cfg, full_cfg={"a": 1},
        )
        assert job.target_cfg is cfg
        assert job.full_cfg == {"a": 1}


# ===================================================================
# TestRunOrchestration
# ===================================================================

class TestRunOrchestration:

    def test_creates_and_finalises_job_run(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        job.job_run_repo.create.assert_called_once()
        job.job_run_repo.finalize.assert_called_once()

    def test_finalize_status_success_when_all_pass(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["status"] == "SUCCESS"
        assert call_kwargs.kwargs["items_succeeded"] == 2
        assert call_kwargs.kwargs["items_failed"] == 0

    def test_finalize_status_failed_when_any_fail(self):
        ingestor, indicator = _setup_clients()
        # MCSA calls get_ohlcv_range twice per ticker (trend + volume).
        # Ticker 1 (AAPL) succeeds (2 calls), ticker 2 (MSFT) fails.
        ingestor.get_ohlcv_range.side_effect = [
            _make_ohlcv_rows(60),  # AAPL trend
            _make_ohlcv_rows(60),  # AAPL volume
            ValueError("no data"),  # MSFT trend → fails
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["status"] == "FAILED"
        assert call_kwargs.kwargs["items_succeeded"] == 1
        assert call_kwargs.kwargs["items_failed"] == 1

    def test_continues_on_ticker_failure(self):
        ingestor, indicator = _setup_clients()
        # Ticker 1 (AAPL) fails on first ohlcv call, ticker 2 (MSFT) succeeds.
        ingestor.get_ohlcv_range.side_effect = [
            ValueError("no data"),   # AAPL trend → fails
            _make_ohlcv_rows(60),    # MSFT trend
            _make_ohlcv_rows(60),    # MSFT volume
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        assert job.job_run_item_repo.create.call_count == 2
        statuses = [
            c.kwargs["status"]
            for c in job.job_run_item_repo.create.call_args_list
        ]
        assert "SUCCESS" in statuses
        assert "FAILED" in statuses

    def test_upsert_called_for_each_success(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        assert job.mcsa_result_repo.upsert.call_count == 2

    def test_single_ticker_override(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run(ticker="GOOG")

        ingestor.get_index_members.assert_not_called()
        assert job.mcsa_result_repo.upsert.call_count == 1
        upserted = job.mcsa_result_repo.upsert.call_args[0][0][0]
        assert upserted["ticker"] == "GOOG"

    def test_ticker_override_normalised_to_uppercase(self):
        """Lowercase ticker override is normalised to UPPER before persistence."""
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run(ticker="aapl")

        upserted = job.mcsa_result_repo.upsert.call_args[0][0][0]
        assert upserted["ticker"] == "AAPL"

    def test_index_tickers_normalised_to_uppercase(self):
        """Tickers from index members are normalised to UPPER."""
        ingestor, indicator = _setup_clients()
        ingestor.get_index_members.return_value = [
            {"symbol": "msft", "instrument_id": "id-1"},
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        upserted = job.mcsa_result_repo.upsert.call_args[0][0][0]
        assert upserted["ticker"] == "MSFT"

    def test_limit_caps_tickers(self):
        ingestor, indicator = _setup_clients()
        ingestor.get_index_members.return_value = [
            {"symbol": f"S{i}"} for i in range(10)
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run(limit=3)

        assert job.mcsa_result_repo.upsert.call_count == 3

    def test_job_run_item_records_error_summary(self):
        ingestor, indicator = _setup_clients()
        ingestor.get_index_members.return_value = [{"symbol": "BAD"}]
        ingestor.get_ohlcv_range.side_effect = RuntimeError("timeout")
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_item_repo.create.call_args
        assert "RuntimeError" in call_kwargs.kwargs["error_summary"]


# ===================================================================
# TestProcessTicker
# ===================================================================

class TestProcessTicker:

    def test_returns_dict_with_required_keys(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            country="US",
            job_run_id=_SAMPLE_UUID,
        )

        required_keys = {
            "ticker", "instrument_id", "as_of_date",
            "mcsa_score", "mcsa_band",
            "trend_score", "vcp_component",
            "volume_score", "fundamental_score",
            "evidence_json", "missing_fields",
            "created_by_job_run_id",
        }
        assert required_keys.issubset(result.keys())

    def test_ticker_in_result(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "MSFT", instrument_id=None, country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["ticker"] == "MSFT"

    def test_score_is_numeric(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        assert isinstance(result["mcsa_score"], (int, float))
        assert 0 <= result["mcsa_score"] <= 100

    def test_band_is_valid(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["mcsa_band"] in ("strong", "watchlist", "neutral", "weak")

    def test_evidence_json_has_sections(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        ej = result["evidence_json"]
        assert "trend" in ej
        assert "vcp" in ej
        assert "volume" in ej
        assert "fundamentals" in ej

    def test_as_of_date_is_today(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["as_of_date"] == date.today().isoformat()

    def test_job_run_id_stored(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["created_by_job_run_id"] == str(_SAMPLE_UUID)

    def test_component_scores_are_numeric(self):
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id="id-1", country="US", job_run_id=_SAMPLE_UUID,
        )
        for key in ("trend_score", "vcp_component", "volume_score", "fundamental_score"):
            assert isinstance(result[key], (int, float)), f"{key} not numeric"

    def test_no_vcp_result_uses_defaults(self):
        """When VCP repo returns None for ticker, VcpInput is empty."""
        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)
        job.vcp_read_repo.get_latest_by_ticker.return_value = None

        result = job._process_ticker(
            "NEW", instrument_id=None, country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["vcp_component"] == 0.0

    def test_no_fundamentals_uses_defaults(self):
        """When fundamentals API returns None, FundamentalsInput is empty."""
        ingestor, indicator = _setup_clients()
        ingestor.get_fundamentals_latest.return_value = None
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL", instrument_id=None, country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["fundamental_score"] == 0.0

    def test_indicator_none_graceful(self):
        """When indicator API returns None, trend uses None values."""
        ingestor = MagicMock()
        ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)
        ingestor.get_fundamentals_latest.return_value = None

        indicator = MagicMock()
        indicator.get_latest.return_value = None

        job = _build_job(ingestor=ingestor, indicator=indicator)
        job.vcp_read_repo.get_latest_by_ticker.return_value = None

        result = job._process_ticker(
            "AAPL", instrument_id=None, country="US", job_run_id=_SAMPLE_UUID,
        )
        assert result["mcsa_score"] >= 0.0

    def test_trend_lookback_uses_config_trend_days(self):
        """OHLCV fetch for latest price uses mcsa_cfg.lookbacks.trend_days, not a hardcoded value."""
        from datetime import date, timedelta

        ingestor, indicator = _setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        # Override trend_days to a non-default value via target config
        from tayfin_screener_jobs.mcsa.config import build_mcsa_config
        target_cfg = _target_cfg()
        target_cfg["mcsa"]["lookbacks"] = {"trend_days": 14}
        job.mcsa_cfg = build_mcsa_config(target_cfg["mcsa"])

        job._process_ticker("AAPL", instrument_id=None, country="US", job_run_id=_SAMPLE_UUID)

        today = date.today()
        expected_from = (today - timedelta(days=14)).isoformat()
        expected_to = today.isoformat()

        # First ohlcv call is for trend (latest price); check from_date uses trend_days
        first_call = ingestor.get_ohlcv_range.call_args_list[0]
        assert first_call[0][1] == expected_from
        assert first_call[0][2] == expected_to
