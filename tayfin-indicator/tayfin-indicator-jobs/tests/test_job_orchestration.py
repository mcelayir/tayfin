"""Job orchestration tests — monkeypatch IngestorClient + repositories.

Validates:
* job_run created + finalized
* job_run_items created per ticker
* AAPL SUCCESS, MSFT FAILED (raises)
* overall job_run FAILED when any item fails
* indicator rows collected for AAPL only

No real HTTP, no real DB.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from conftest import make_ohlcv_candles

# We test MaComputeJob as the representative; the orchestration logic is
# identical across all four job classes.


# ── Fake collaborators ───────────────────────────────────────────────


class FakeJobRunRepository:
    """Captures create / finalize calls."""

    def __init__(self):
        self.runs: list[dict] = []
        self._counter = 0

    def create(self, **kwargs) -> str:
        self._counter += 1
        run_id = f"run-{self._counter}"
        self.runs.append({"id": run_id, **kwargs})
        return run_id

    def finalize(self, **kwargs) -> None:
        self.runs[-1].update(kwargs)


class FakeJobRunItemRepository:
    """Captures create calls."""

    def __init__(self):
        self.items: list[dict] = []
        self._counter = 0

    def create(self, **kwargs) -> str:
        self._counter += 1
        item_id = f"item-{self._counter}"
        self.items.append({"id": item_id, **kwargs})
        return item_id


class FakeIndicatorSeriesRepository:
    """Captures upsert calls and returns row count."""

    def __init__(self):
        self.upserted_rows: list[dict] = []

    def upsert_indicator_rows(self, rows: list[dict]) -> int:
        self.upserted_rows.extend(rows)
        return len(rows)


class FakeIngestorClient:
    """Return fixed ticker list; AAPL gets candles, MSFT raises."""

    def __init__(self, aapl_candles: list[dict]):
        self._aapl_candles = aapl_candles

    def get_index_instruments(self, index_code: str) -> list[dict]:
        return [{"ticker": "AAPL"}, {"ticker": "MSFT"}]

    def get_ohlcv_range(self, ticker: str, start_date, end_date) -> list[dict]:
        if ticker == "AAPL":
            return self._aapl_candles
        raise ConnectionError(f"simulated network failure for {ticker}")


# ── Helpers ──────────────────────────────────────────────────────────


def _build_job(monkeypatch, candles):
    """Build an MaComputeJob with all dependencies faked."""
    # Prevent get_engine() from touching a real DB
    monkeypatch.setattr(
        "tayfin_indicator_jobs.jobs.ma_compute_job.get_engine",
        lambda: MagicMock(),
    )

    from tayfin_indicator_jobs.jobs.ma_compute_job import MaComputeJob

    target_cfg = {
        "index_code": "NDX",
        "country": "US",
        "indicators": [
            {"key": "sma", "params": {"window": 3}},
        ],
    }
    job = MaComputeJob(
        target_name="test-target",
        target_cfg=target_cfg,
        full_cfg={"jobs": {"ma_compute": {"test-target": target_cfg}}},
    )
    # Inject fakes
    job.job_run_repo = FakeJobRunRepository()
    job.job_run_item_repo = FakeJobRunItemRepository()
    job.indicator_repo = FakeIndicatorSeriesRepository()
    job.ingestor = FakeIngestorClient(candles)
    return job


# ── Tests ────────────────────────────────────────────────────────────


class TestMaComputeJobOrchestration:
    """Integration-style test of the MaComputeJob orchestration loop."""

    def test_aapl_success_msft_failure(self, monkeypatch):
        """AAPL succeeds, MSFT fails → overall FAILED."""
        monkeypatch.setenv("TAYFIN_INDICATOR_LOOKBACK_DAYS", "420")
        candles = make_ohlcv_candles(n=10, base_close=100.0)
        job = _build_job(monkeypatch, candles)

        job.run()

        # ── job_run ─────────────────────────────────────────────
        assert len(job.job_run_repo.runs) == 1
        run = job.job_run_repo.runs[0]
        assert run["job_name"] == "ma_compute"
        # finalize should have been called with FAILED (MSFT failed)
        assert run["status"] == "FAILED"

        # ── job_run_items ───────────────────────────────────────
        items = job.job_run_item_repo.items
        assert len(items) == 2

        aapl_item = next(i for i in items if i["item_key"] == "AAPL")
        msft_item = next(i for i in items if i["item_key"] == "MSFT")
        assert aapl_item["status"] == "SUCCESS"
        assert msft_item["status"] == "FAILED"
        assert "simulated network failure" in (msft_item["message"] or "")

        # ── indicator rows ──────────────────────────────────────
        # SMA(3) on 10 candles → 8 rows (indices 2..9)
        upserted = job.indicator_repo.upserted_rows
        assert len(upserted) == 8
        assert all(r["ticker"] == "AAPL" for r in upserted)
        assert all(r["indicator_key"] == "sma" for r in upserted)
        # No MSFT rows
        assert not any(r["ticker"] == "MSFT" for r in upserted)

    def test_all_success(self, monkeypatch):
        """When all tickers succeed, overall status is SUCCESS."""
        monkeypatch.setenv("TAYFIN_INDICATOR_LOOKBACK_DAYS", "420")
        candles = make_ohlcv_candles(n=10, base_close=100.0)

        monkeypatch.setattr(
            "tayfin_indicator_jobs.jobs.ma_compute_job.get_engine",
            lambda: MagicMock(),
        )

        from tayfin_indicator_jobs.jobs.ma_compute_job import MaComputeJob

        target_cfg = {
            "index_code": "NDX",
            "country": "US",
            "indicators": [{"key": "sma", "params": {"window": 3}}],
        }
        job = MaComputeJob(
            target_name="test-target",
            target_cfg=target_cfg,
            full_cfg={"jobs": {"ma_compute": {"test-target": target_cfg}}},
        )
        job.job_run_repo = FakeJobRunRepository()
        job.job_run_item_repo = FakeJobRunItemRepository()
        job.indicator_repo = FakeIndicatorSeriesRepository()

        # All tickers return candles successfully
        class AllSuccessClient:
            def get_index_instruments(self, index_code):
                return [{"ticker": "AAPL"}, {"ticker": "MSFT"}]

            def get_ohlcv_range(self, ticker, start_date, end_date):
                return candles

        job.ingestor = AllSuccessClient()
        job.run()

        run = job.job_run_repo.runs[0]
        assert run["status"] == "SUCCESS"

        items = job.job_run_item_repo.items
        assert all(i["status"] == "SUCCESS" for i in items)

    def test_empty_candles_still_success(self, monkeypatch):
        """Ticker with no candles → item SUCCESS (no rows written)."""
        monkeypatch.setenv("TAYFIN_INDICATOR_LOOKBACK_DAYS", "420")

        monkeypatch.setattr(
            "tayfin_indicator_jobs.jobs.ma_compute_job.get_engine",
            lambda: MagicMock(),
        )

        from tayfin_indicator_jobs.jobs.ma_compute_job import MaComputeJob

        target_cfg = {
            "index_code": "NDX",
            "country": "US",
            "indicators": [{"key": "sma", "params": {"window": 3}}],
        }
        job = MaComputeJob(
            target_name="test-target",
            target_cfg=target_cfg,
            full_cfg={},
        )
        job.job_run_repo = FakeJobRunRepository()
        job.job_run_item_repo = FakeJobRunItemRepository()
        job.indicator_repo = FakeIndicatorSeriesRepository()

        class EmptyCandlesClient:
            def get_index_instruments(self, index_code):
                return [{"ticker": "AAPL"}]

            def get_ohlcv_range(self, ticker, start_date, end_date):
                return []

        job.ingestor = EmptyCandlesClient()
        job.run()

        run = job.job_run_repo.runs[0]
        assert run["status"] == "SUCCESS"

        aapl_item = job.job_run_item_repo.items[0]
        assert aapl_item["status"] == "SUCCESS"
        assert job.indicator_repo.upserted_rows == []

    def test_sma_values_are_correct(self, monkeypatch):
        """Verify the actual SMA values written match hand-calc."""
        monkeypatch.setenv("TAYFIN_INDICATOR_LOOKBACK_DAYS", "420")
        # close = 100, 101, 102, 103, 104
        candles = make_ohlcv_candles(n=5, base_close=100.0, step=1.0)

        monkeypatch.setattr(
            "tayfin_indicator_jobs.jobs.ma_compute_job.get_engine",
            lambda: MagicMock(),
        )

        from tayfin_indicator_jobs.jobs.ma_compute_job import MaComputeJob

        target_cfg = {
            "index_code": "NDX",
            "country": "US",
            "indicators": [{"key": "sma", "params": {"window": 3}}],
        }
        job = MaComputeJob(
            target_name="t",
            target_cfg=target_cfg,
            full_cfg={},
        )
        job.job_run_repo = FakeJobRunRepository()
        job.job_run_item_repo = FakeJobRunItemRepository()
        job.indicator_repo = FakeIndicatorSeriesRepository()

        class SingleTickerClient:
            def get_index_instruments(self, index_code):
                return [{"ticker": "AAPL"}]

            def get_ohlcv_range(self, ticker, start_date, end_date):
                return candles

        job.ingestor = SingleTickerClient()
        job.run()

        rows = job.indicator_repo.upserted_rows
        # SMA(3) on [100,101,102,103,104] → 3 values at idx 2,3,4
        assert len(rows) == 3
        values = [r["value"] for r in rows]
        assert values[0] == pytest.approx(101.0, abs=0.01)  # (100+101+102)/3
        assert values[1] == pytest.approx(102.0, abs=0.01)  # (101+102+103)/3
        assert values[2] == pytest.approx(103.0, abs=0.01)  # (102+103+104)/3
