"""Failure-path tests for OHLCV backfill orchestration.

Validates:
- Transient TradingView failures trigger retries then fallback to yfinance
- Per-ticker failures do not stop the job
- Audit records (job_run_items) accurately reflect outcomes
- Overall job_run status = FAILED when any item fails

Uses real Postgres (docker-compose local DB) with fake providers.
No real network calls are made.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import text

from tayfin_ingestor_jobs.db.engine import get_engine
from tayfin_ingestor_jobs.ohlcv.providers.base import (
    PermanentProviderError,
    TransientProviderError,
)
from tayfin_ingestor_jobs.ohlcv.service import run_ohlcv_ingestion


# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------

class FakeTradingViewProvider:
    """Always fails — raises TransientProviderError for every call.

    Tracks call counts per ticker so tests can assert retries happened.
    """

    def __init__(self):
        self.call_counts: dict[str, int] = defaultdict(int)

    def fetch_daily(
        self, exchange: str, symbol: str,
        start_date: str | None = None, end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        self.call_counts[symbol] += 1
        raise TransientProviderError(
            f"fake-tv: simulated transient failure for {symbol} "
            f"(call #{self.call_counts[symbol]})"
        )


class FakeYfinanceProviderPartial:
    """AAPL → returns valid data.  MSFT → raises PermanentProviderError."""

    def __init__(self, start: date, end: date):
        self._start = start
        self._end = end
        self.call_counts: dict[str, int] = defaultdict(int)

    def fetch_daily(
        self, exchange: str, symbol: str,
        start_date: str | None = None, end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame:
        self.call_counts[symbol] += 1

        if symbol == "AAPL":
            return self._make_df(start_date or str(self._start),
                                 end_date or str(self._end))

        # MSFT and anything else → total failure
        raise PermanentProviderError(
            f"fake-yf: permanent failure for {symbol}"
        )

    @staticmethod
    def _make_df(start: str, end: str) -> pd.DataFrame:
        """Create a small valid OHLCV DataFrame within the requested window."""
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
        days = []
        cursor = s
        while cursor <= e and len(days) < 5:
            # skip weekends
            if cursor.weekday() < 5:
                days.append(cursor)
            cursor += timedelta(days=1)
        if not days:
            days = [s]
        return pd.DataFrame({
            "date": [d.isoformat() for d in days],
            "open":  [150.0 + i for i in range(len(days))],
            "high":  [155.0 + i for i in range(len(days))],
            "low":   [148.0 + i for i in range(len(days))],
            "close": [152.0 + i for i in range(len(days))],
            "volume": [1_000_000 + i * 100 for i in range(len(days))],
        })


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    return get_engine()


@pytest.fixture()
def _seed_instruments(engine):
    """Insert AAPL + MSFT instruments and NDX index memberships.

    Uses ON CONFLICT DO NOTHING so the test is re-runnable.
    Cleans up ohlcv_daily rows for the test tickers afterward.
    """
    with engine.begin() as conn:
        # Need a job_run for the FK on instruments.created_by_job_run_id
        row = conn.execute(text("""
            INSERT INTO tayfin_ingestor.job_runs
                (job_name, trigger_type, status, started_at)
            VALUES ('test_setup', 'TEST', 'SUCCESS', now())
            RETURNING id
        """)).fetchone()
        setup_run_id = row[0]

        for ticker in ("AAPL", "MSFT"):
            conn.execute(text("""
                INSERT INTO tayfin_ingestor.instruments
                    (ticker, country, exchange, created_by_job_run_id)
                VALUES (:ticker, 'US', 'NASDAQ', :run_id)
                ON CONFLICT (ticker, country) DO NOTHING
            """), {"ticker": ticker, "run_id": setup_run_id})

        # Resolve instrument IDs
        ids = {}
        for ticker in ("AAPL", "MSFT"):
            r = conn.execute(text("""
                SELECT id FROM tayfin_ingestor.instruments
                WHERE ticker = :ticker AND country = 'US'
            """), {"ticker": ticker}).fetchone()
            ids[ticker] = r[0]

        for ticker, inst_id in ids.items():
            conn.execute(text("""
                INSERT INTO tayfin_ingestor.index_memberships
                    (index_code, instrument_id, country, created_by_job_run_id)
                VALUES ('TEST_BACKFILL', :inst_id, 'US', :run_id)
                ON CONFLICT (index_code, instrument_id) DO NOTHING
            """), {"inst_id": inst_id, "run_id": setup_run_id})

    yield ids

    # Cleanup: remove ohlcv_daily rows and test memberships created during this test
    with engine.begin() as conn:
        for inst_id in ids.values():
            conn.execute(text("""
                DELETE FROM tayfin_ingestor.ohlcv_daily
                WHERE instrument_id = :inst_id
                  AND as_of_date BETWEEN :start AND :end
            """), {
                "inst_id": inst_id,
                "start": date.today() - timedelta(days=30),
                "end": date.today(),
            })
        conn.execute(text("""
            DELETE FROM tayfin_ingestor.index_memberships
            WHERE index_code = 'TEST_BACKFILL'
        """))


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("_seed_instruments")
class TestOhlcvBackfillFailurePaths:
    """Integration test: fake providers → real DB → real orchestration."""

    CFG = {
        "code": "test_backfill",
        "country": "US",
        "index_code": "TEST_BACKFILL",
        "timeframe": "1d",
        "default_exchange": "NASDAQ",
        "window_days": 400,
    }

    def test_fallback_and_total_failure(
        self, engine, _seed_instruments, monkeypatch,
    ):
        """AAPL: TV fails → yfinance succeeds.  MSFT: both fail."""
        start = date.today() - timedelta(days=14)
        end = date.today()

        fake_tv = FakeTradingViewProvider()
        fake_yf = FakeYfinanceProviderPartial(start, end)

        # Monkeypatch provider constructors in the service module
        monkeypatch.setattr(
            "tayfin_ingestor_jobs.ohlcv.service.TradingViewOhlcvProvider",
            lambda: fake_tv,
        )
        monkeypatch.setattr(
            "tayfin_ingestor_jobs.ohlcv.service.YfinanceOhlcvProvider",
            lambda: fake_yf,
        )

        # Disable retry delays for speed
        monkeypatch.setenv("OHLCV_PROVIDER_MAX_RETRIES", "2")
        monkeypatch.setenv("OHLCV_PROVIDER_BACKOFF_SECONDS", "0")
        monkeypatch.setenv("OHLCV_TV_MIN_DELAY_SECONDS", "0")

        summary = run_ohlcv_ingestion(
            target_name="NDX",
            cfg=self.CFG,
            start_date=start,
            end_date=end,
            engine=engine,
        )

        # ----- Overall run -----
        assert summary["status"] == "FAILED", (
            "Job must be FAILED when at least one ticker fails"
        )
        assert summary["total"] == 2
        assert summary["succeeded"] == 1
        assert summary["failed"] == 1

        items_by_ticker = {i["ticker"]: i for i in summary["items"]}

        # ----- AAPL: fallback success -----
        aapl = items_by_ticker["AAPL"]
        assert aapl["status"] == "SUCCESS"
        assert aapl["skipped"] is False
        assert aapl["provider_used"] == "yfinance"
        assert aapl["rows_written"] > 0

        # TradingView must have been called (retries)
        assert fake_tv.call_counts["AAPL"] >= 2, (
            f"Expected at least 2 TV calls for AAPL, got {fake_tv.call_counts['AAPL']}"
        )
        # yfinance must have been called exactly once
        assert fake_yf.call_counts["AAPL"] >= 1

        # ----- MSFT: total failure -----
        msft = items_by_ticker["MSFT"]
        assert msft["status"] == "FAILED"
        assert msft["rows_written"] == 0
        assert msft["error"] is not None

        # ----- DB: AAPL rows exist -----
        aapl_id = _seed_instruments["AAPL"]
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT COUNT(*), MIN(as_of_date), MAX(as_of_date)
                FROM tayfin_ingestor.ohlcv_daily
                WHERE instrument_id = :inst_id
                  AND as_of_date BETWEEN :start AND :end
            """), {"inst_id": aapl_id, "start": start, "end": end}).fetchone()

        aapl_count, aapl_min, aapl_max = row
        assert aapl_count > 0, "AAPL should have OHLCV rows in DB"
        assert aapl_count == aapl["rows_written"]

        # ----- DB: MSFT has no rows in window -----
        msft_id = _seed_instruments["MSFT"]
        with engine.connect() as conn:
            msft_count = conn.execute(text("""
                SELECT COUNT(*)
                FROM tayfin_ingestor.ohlcv_daily
                WHERE instrument_id = :inst_id
                  AND as_of_date BETWEEN :start AND :end
            """), {"inst_id": msft_id, "start": start, "end": end}).fetchone()[0]

        assert msft_count == 0, "MSFT should have no OHLCV rows"

        # ----- DB: job_run status -----
        job_run_id = summary["job_run_id"]
        with engine.connect() as conn:
            jr = conn.execute(text("""
                SELECT status, items_total, items_succeeded, items_failed
                FROM tayfin_ingestor.job_runs
                WHERE id = :id
            """), {"id": job_run_id}).fetchone()

        assert jr[0] == "FAILED"
        assert jr[1] == 2  # items_total
        assert jr[2] == 1  # items_succeeded
        assert jr[3] == 1  # items_failed

        # ----- DB: job_run_items -----
        with engine.connect() as conn:
            items_rows = conn.execute(text("""
                SELECT item_key, status, error_summary, error_details
                FROM tayfin_ingestor.job_run_items
                WHERE job_run_id = :id
                ORDER BY item_key
            """), {"id": job_run_id}).fetchall()

        audit = {r[0]: r for r in items_rows}

        # AAPL audit: SUCCESS, details mention yfinance
        aapl_audit = audit["AAPL"]
        assert aapl_audit[1] == "SUCCESS"
        # error_details is jsonb — psycopg returns it as a dict already
        aapl_details = aapl_audit[3] if isinstance(aapl_audit[3], dict) else json.loads(aapl_audit[3] or "{}")
        assert aapl_details.get("provider") == "yfinance"

        # MSFT audit: FAILED, error summary present
        msft_audit = audit["MSFT"]
        assert msft_audit[1] == "FAILED"
        assert msft_audit[2] is not None or msft_audit[3] is not None, (
            "MSFT audit must have error_summary or error_details"
        )
