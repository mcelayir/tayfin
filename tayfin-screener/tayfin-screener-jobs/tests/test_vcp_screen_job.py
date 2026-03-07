"""Tests for tayfin_screener_jobs.jobs.vcp_screen_job."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from tayfin_screener_jobs.jobs.vcp_screen_job import (
    VcpScreenJob,
    _build_indicator_map,
    _ohlcv_to_dataframe,
)


# ===================================================================
# Fixtures & helpers
# ===================================================================

_SAMPLE_UUID = uuid4()


def _make_ohlcv_rows(n: int = 30) -> list[dict]:
    """Return *n* synthetic OHLCV rows with ascending dates."""
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


def _make_indicator_range(n: int = 20, base_value: float = 100.0) -> list[dict]:
    return [
        {
            "as_of_date": (date.today() - timedelta(days=n - i)).isoformat(),
            "value": base_value + i * 0.1,
        }
        for i in range(n)
    ]


def _indicators_cfg() -> list[dict]:
    return [
        {"key": "sma", "window": 50},
        {"key": "sma", "window": 150},
        {"key": "sma", "window": 200},
        {"key": "atr", "window": 20},
        {"key": "vol_sma", "window": 50},
        {"key": "rolling_high", "window": 252},
    ]


def _target_cfg() -> dict:
    return {
        "index_code": "NDX",
        "country": "US",
        "lookback_days": 365,
        "indicators": _indicators_cfg(),
    }


def _mock_repos():
    """Return mocked repo instances."""
    job_run_repo = MagicMock()
    job_run_repo.create.return_value = _SAMPLE_UUID

    job_run_item_repo = MagicMock()
    job_run_item_repo.create.return_value = uuid4()

    vcp_result_repo = MagicMock()
    vcp_result_repo.upsert.return_value = 1

    return job_run_repo, job_run_item_repo, vcp_result_repo


def _build_job(
    *,
    ingestor=None,
    indicator=None,
    target_cfg=None,
) -> VcpScreenJob:
    """Build a VcpScreenJob with mocked dependencies."""
    jr, jri, vcp = _mock_repos()

    _ingestor = ingestor or MagicMock()
    _indicator = indicator or MagicMock()

    job = VcpScreenJob(
        target_name="test-target",
        target_cfg=target_cfg or _target_cfg(),
        full_cfg={"jobs": {"vcp_screen": {"targets": {"test-target": _target_cfg()}}}},
        engine=MagicMock(),
        ingestor_client=_ingestor,
        indicator_client=_indicator,
        job_run_repo=jr,
        job_run_item_repo=jri,
        vcp_result_repo=vcp,
    )
    return job


# ===================================================================
# TestBuildIndicatorMap
# ===================================================================

class TestBuildIndicatorMap:
    """Tests for :func:`_build_indicator_map`."""

    def test_basic_mapping(self):
        cfg = [{"key": "sma", "window": 50}, {"key": "atr", "window": 20}]
        result = _build_indicator_map(cfg)
        assert result == {"sma_50": ("sma", 50), "atr_20": ("atr", 20)}

    def test_duplicate_keys_different_windows(self):
        cfg = [
            {"key": "sma", "window": 50},
            {"key": "sma", "window": 150},
            {"key": "sma", "window": 200},
        ]
        result = _build_indicator_map(cfg)
        assert len(result) == 3
        assert result["sma_50"] == ("sma", 50)
        assert result["sma_150"] == ("sma", 150)
        assert result["sma_200"] == ("sma", 200)

    def test_empty_config(self):
        assert _build_indicator_map([]) == {}

    def test_window_coerced_to_int(self):
        result = _build_indicator_map([{"key": "atr", "window": "20"}])
        assert result["atr_20"] == ("atr", 20)


# ===================================================================
# TestOhlcvToDataframe
# ===================================================================

class TestOhlcvToDataframe:
    """Tests for :func:`_ohlcv_to_dataframe`."""

    def test_sorted_by_date(self):
        rows = _make_ohlcv_rows(10)
        # Shuffle to verify sorting
        import random
        random.shuffle(rows)
        df = _ohlcv_to_dataframe(rows)
        dates = df["as_of_date"].tolist()
        assert dates == sorted(dates)

    def test_numeric_columns(self):
        df = _ohlcv_to_dataframe(_make_ohlcv_rows(5))
        for col in ("open", "high", "low", "close", "volume"):
            assert df[col].dtype.kind in ("i", "f")  # int or float

    def test_shape(self):
        df = _ohlcv_to_dataframe(_make_ohlcv_rows(20))
        assert len(df) == 20

    def test_index_reset(self):
        df = _ohlcv_to_dataframe(_make_ohlcv_rows(5))
        assert list(df.index) == [0, 1, 2, 3, 4]


# ===================================================================
# TestFromConfig
# ===================================================================

class TestFromConfig:
    """Tests for :meth:`VcpScreenJob.from_config`."""

    @patch("tayfin_screener_jobs.jobs.vcp_screen_job.get_engine")
    def test_returns_instance(self, mock_engine):
        mock_engine.return_value = MagicMock()
        job = VcpScreenJob.from_config(
            target_name="nasdaq-100",
            target_cfg=_target_cfg(),
            full_cfg={},
        )
        assert isinstance(job, VcpScreenJob)
        assert job.target_name == "nasdaq-100"

    @patch("tayfin_screener_jobs.jobs.vcp_screen_job.get_engine")
    def test_stores_config(self, mock_engine):
        mock_engine.return_value = MagicMock()
        cfg = _target_cfg()
        job = VcpScreenJob.from_config(
            target_name="t", target_cfg=cfg, full_cfg={"a": 1},
        )
        assert job.target_cfg is cfg
        assert job.full_cfg == {"a": 1}


# ===================================================================
# TestRunOrchestration
# ===================================================================

class TestRunOrchestration:
    """Tests for :meth:`VcpScreenJob.run`."""

    def _setup_clients(self):
        """Build ingestor + indicator mocks that return valid data."""
        ingestor = MagicMock()
        ingestor.get_index_members.return_value = [
            {"symbol": "AAPL", "instrument_id": "id-1"},
            {"symbol": "MSFT", "instrument_id": "id-2"},
        ]
        ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)

        indicator = MagicMock()
        indicator.get_latest.return_value = _make_indicator_latest(150.0)
        indicator.get_range.return_value = _make_indicator_range(20, 100.0)

        return ingestor, indicator

    def test_creates_and_finalises_job_run(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        job.job_run_repo.create.assert_called_once()
        job.job_run_repo.finalize.assert_called_once()

    def test_finalize_status_success_when_all_pass(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["status"] == "SUCCESS"
        assert call_kwargs.kwargs["items_succeeded"] == 2
        assert call_kwargs.kwargs["items_failed"] == 0

    def test_finalize_status_failed_when_any_fail(self):
        ingestor, indicator = self._setup_clients()
        # First ticker succeeds, second raises
        ingestor.get_ohlcv_range.side_effect = [
            _make_ohlcv_rows(60),
            ValueError("no data"),
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["status"] == "FAILED"
        assert call_kwargs.kwargs["items_succeeded"] == 1
        assert call_kwargs.kwargs["items_failed"] == 1

    def test_continues_on_ticker_failure(self):
        ingestor, indicator = self._setup_clients()
        # First ticker fails, second succeeds
        ingestor.get_ohlcv_range.side_effect = [
            ValueError("no data"),
            _make_ohlcv_rows(60),
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        # Both tickers processed
        assert job.job_run_item_repo.create.call_count == 2
        statuses = [
            c.kwargs["status"]
            for c in job.job_run_item_repo.create.call_args_list
        ]
        assert "SUCCESS" in statuses
        assert "FAILED" in statuses

    def test_upsert_called_for_each_success(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        assert job.vcp_result_repo.upsert.call_count == 2

    def test_single_ticker_override(self):
        ingestor, indicator = self._setup_clients()
        ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run(ticker="GOOG")

        # Should NOT call get_index_members
        ingestor.get_index_members.assert_not_called()
        # One ticker processed
        assert job.vcp_result_repo.upsert.call_count == 1
        upserted = job.vcp_result_repo.upsert.call_args[0][0][0]
        assert upserted["ticker"] == "GOOG"

    def test_limit_caps_tickers(self):
        ingestor, indicator = self._setup_clients()
        ingestor.get_index_members.return_value = [
            {"symbol": f"S{i}"} for i in range(10)
        ]
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run(limit=3)

        assert job.vcp_result_repo.upsert.call_count == 3

    def test_empty_ohlcv_raises_for_ticker(self):
        ingestor, indicator = self._setup_clients()
        ingestor.get_index_members.return_value = [{"symbol": "EMPTY"}]
        ingestor.get_ohlcv_range.return_value = []
        job = _build_job(ingestor=ingestor, indicator=indicator)

        job.run()

        call_kwargs = job.job_run_repo.finalize.call_args
        assert call_kwargs.kwargs["items_failed"] == 1

    def test_job_run_item_records_error_summary(self):
        ingestor, indicator = self._setup_clients()
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
    """Tests for :meth:`VcpScreenJob._process_ticker`."""

    def _setup_clients(self):
        ingestor = MagicMock()
        ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)

        indicator = MagicMock()
        indicator.get_latest.return_value = _make_indicator_latest(150.0)
        indicator.get_range.return_value = _make_indicator_range(20, 100.0)

        return ingestor, indicator

    def test_returns_dict_with_required_keys(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )

        required_keys = {
            "ticker", "instrument_id", "as_of_date",
            "vcp_score", "vcp_confidence", "pattern_detected",
            "features_json", "created_by_job_run_id",
        }
        assert required_keys.issubset(result.keys())

    def test_ticker_in_result(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "MSFT",
            instrument_id=None,
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert result["ticker"] == "MSFT"

    def test_score_is_numeric(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert isinstance(result["vcp_score"], (int, float))
        assert 0 <= result["vcp_score"] <= 100

    def test_features_json_has_sections(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        fj = result["features_json"]
        assert "contraction" in fj
        assert "volatility" in fj
        assert "volume" in fj
        assert "breakdown" in fj

    def test_confidence_is_valid_tier(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert result["vcp_confidence"] in ("high", "medium", "low")

    def test_pattern_detected_is_bool(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert isinstance(result["pattern_detected"], bool)

    def test_as_of_date_is_today(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert result["as_of_date"] == date.today().isoformat()

    def test_job_run_id_stored(self):
        ingestor, indicator = self._setup_clients()
        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id="id-1",
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        assert result["created_by_job_run_id"] == str(_SAMPLE_UUID)

    def test_no_ohlcv_raises(self):
        ingestor = MagicMock()
        ingestor.get_ohlcv_range.return_value = []
        job = _build_job(ingestor=ingestor)

        with pytest.raises(ValueError, match="No OHLCV data"):
            job._process_ticker(
                "AAPL",
                instrument_id=None,
                lookback_days=365,
                indicators_cfg=_indicators_cfg(),
                job_run_id=_SAMPLE_UUID,
            )

    def test_indicator_none_uses_defaults(self):
        """When indicator API returns None, features use 0.0 defaults."""
        ingestor = MagicMock()
        ingestor.get_ohlcv_range.return_value = _make_ohlcv_rows(60)

        indicator = MagicMock()
        indicator.get_latest.return_value = None
        indicator.get_range.return_value = []

        job = _build_job(ingestor=ingestor, indicator=indicator)

        result = job._process_ticker(
            "AAPL",
            instrument_id=None,
            lookback_days=365,
            indicators_cfg=_indicators_cfg(),
            job_run_id=_SAMPLE_UUID,
        )
        # Should still produce a valid result (with low score)
        assert result["vcp_score"] >= 0


# ===================================================================
# TestFetchIndicators
# ===================================================================

class TestFetchIndicators:
    """Tests for :meth:`VcpScreenJob._fetch_indicators`."""

    def test_latest_populated(self):
        indicator = MagicMock()
        indicator.get_latest.return_value = _make_indicator_latest(200.0)
        indicator.get_range.return_value = []
        job = _build_job(indicator=indicator)

        ind_map = {"sma_50": ("sma", 50)}
        latest, ranges = job._fetch_indicators(
            "AAPL", ind_map, "2025-01-01", "2025-12-31",
        )
        assert latest["sma_50"] == 200.0

    def test_range_populated(self):
        indicator = MagicMock()
        indicator.get_latest.return_value = None
        indicator.get_range.return_value = [
            {"as_of_date": "2025-06-01", "value": 10.5},
            {"as_of_date": "2025-06-02", "value": 11.0},
        ]
        job = _build_job(indicator=indicator)

        ind_map = {"atr_20": ("atr", 20)}
        latest, ranges = job._fetch_indicators(
            "AAPL", ind_map, "2025-01-01", "2025-12-31",
        )
        assert ranges["atr_20"] == [10.5, 11.0]

    def test_none_latest_skipped(self):
        indicator = MagicMock()
        indicator.get_latest.return_value = None
        indicator.get_range.return_value = []
        job = _build_job(indicator=indicator)

        ind_map = {"sma_50": ("sma", 50)}
        latest, _ = job._fetch_indicators(
            "AAPL", ind_map, "2025-01-01", "2025-12-31",
        )
        assert "sma_50" not in latest

    def test_multiple_indicators(self):
        indicator = MagicMock()
        indicator.get_latest.return_value = _make_indicator_latest(100.0)
        indicator.get_range.return_value = _make_indicator_range(5, 50.0)
        job = _build_job(indicator=indicator)

        ind_map = {
            "sma_50": ("sma", 50),
            "atr_20": ("atr", 20),
        }
        latest, ranges = job._fetch_indicators(
            "AAPL", ind_map, "2025-01-01", "2025-12-31",
        )
        assert len(latest) == 2
        assert len(ranges) == 2

    def test_api_key_passed_correctly(self):
        indicator = MagicMock()
        indicator.get_latest.return_value = None
        indicator.get_range.return_value = []
        job = _build_job(indicator=indicator)

        ind_map = {"rolling_high_252": ("rolling_high", 252)}
        job._fetch_indicators("AAPL", ind_map, "2025-01-01", "2025-12-31")

        # Verify the raw API key ("rolling_high") was used, not the canonical key
        indicator.get_latest.assert_called_once_with("AAPL", "rolling_high", window=252)
        indicator.get_range.assert_called_once_with(
            "AAPL", "rolling_high", "2025-01-01", "2025-12-31", window=252,
        )
