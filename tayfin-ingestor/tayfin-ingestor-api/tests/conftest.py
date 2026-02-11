"""Shared fixtures for tayfin-ingestor-api integration tests.

Strategy:
- Uses the real local Postgres (docker-compose).
- Inserts minimal seed data with far-future dates (2099-*) so it never
  clashes with real ingestion data.
- Cleans up all inserted rows after the test module finishes by tracking
  via ``created_by_job_run_id``.
- Uses a dedicated test index code (``TEST_NDX``) to avoid interference
  with real index memberships.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text

from tayfin_ingestor_api.app import create_app
from tayfin_ingestor_api.db.engine import get_engine


# ------------------------------------------------------------------
# Seed-data constants
# ------------------------------------------------------------------

AAPL_DATES = [date(2099, 1, 10), date(2099, 1, 11), date(2099, 1, 12)]
MSFT_DATES = [date(2099, 1, 11), date(2099, 1, 13)]

TEST_INDEX_CODE = "TEST_NDX"


def _ohlcv_values(
    instrument_id: uuid.UUID,
    as_of_date: date,
    job_run_id: uuid.UUID,
    *,
    open_: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    close: float = 102.0,
    volume: int = 10000,
    source: str = "test",
) -> dict:
    return {
        "instrument_id": str(instrument_id),
        "as_of_date": as_of_date,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "source": source,
        "job_run_id": str(job_run_id),
    }


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_engine():
    """Real SQLAlchemy engine connected to local Postgres."""
    return get_engine()


@pytest.fixture(scope="module")
def seed(db_engine):
    """Insert deterministic test rows; clean up afterwards.

    Yields a dict with the ids/dates tests need for assertions.
    """
    engine = db_engine

    with engine.begin() as conn:
        # 1) Job run (required FK for instruments, ohlcv_daily)
        job_run_id = conn.execute(
            text(
                "INSERT INTO tayfin_ingestor.job_runs "
                "(job_name, trigger_type, status, started_at, finished_at) "
                "VALUES ('test-ohlcv-api', 'test', 'COMPLETED', now(), now()) "
                "RETURNING id"
            )
        ).scalar()

        # 2) Instruments — insert only if not already present
        def _ensure_instrument(conn, ticker, country):
            conn.execute(
                text(
                    "INSERT INTO tayfin_ingestor.instruments (ticker, country, created_by_job_run_id) "
                    "VALUES (:ticker, :country, :jr) "
                    "ON CONFLICT (ticker, country) DO NOTHING"
                ),
                {"ticker": ticker, "country": country, "jr": str(job_run_id)},
            )
            return conn.execute(
                text(
                    "SELECT id FROM tayfin_ingestor.instruments "
                    "WHERE ticker = :ticker AND country = :country"
                ),
                {"ticker": ticker, "country": country},
            ).scalar()

        aapl_id = _ensure_instrument(conn, "AAPL", "US")
        msft_id = _ensure_instrument(conn, "MSFT", "US")

        # 3) Index memberships for TEST_NDX
        for instr_id in (aapl_id, msft_id):
            conn.execute(
                text(
                    "INSERT INTO tayfin_ingestor.index_memberships "
                    "(index_code, instrument_id, country, created_by_job_run_id) "
                    "VALUES (:ic, :iid, 'US', :jr) "
                    "ON CONFLICT (index_code, instrument_id) DO NOTHING"
                ),
                {"ic": TEST_INDEX_CODE, "iid": str(instr_id), "jr": str(job_run_id)},
            )

        # 4) OHLCV rows — AAPL × 3 dates, MSFT × 2 dates
        insert_ohlcv = text(
            "INSERT INTO tayfin_ingestor.ohlcv_daily "
            "(instrument_id, as_of_date, open, high, low, close, volume, source, created_by_job_run_id) "
            "VALUES (:instrument_id, :as_of_date, :open, :high, :low, :close, :volume, :source, :job_run_id) "
            "ON CONFLICT (instrument_id, as_of_date) DO NOTHING"
        )

        for i, d in enumerate(AAPL_DATES):
            conn.execute(
                insert_ohlcv,
                _ohlcv_values(aapl_id, d, job_run_id, open_=100 + i, close=102 + i, volume=10000 + i * 100),
            )
        for i, d in enumerate(MSFT_DATES):
            conn.execute(
                insert_ohlcv,
                _ohlcv_values(msft_id, d, job_run_id, open_=200 + i, close=202 + i, volume=20000 + i * 100),
            )

    yield {
        "job_run_id": job_run_id,
        "aapl_id": aapl_id,
        "msft_id": msft_id,
        "aapl_dates": AAPL_DATES,
        "msft_dates": MSFT_DATES,
        "aapl_latest": max(AAPL_DATES),
        "msft_latest": max(MSFT_DATES),
        "index_code": TEST_INDEX_CODE,
    }

    # ---------- cleanup (reverse FK order) ----------
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tayfin_ingestor.ohlcv_daily WHERE created_by_job_run_id = :jr"),
            {"jr": str(job_run_id)},
        )
        conn.execute(
            text("DELETE FROM tayfin_ingestor.index_memberships WHERE created_by_job_run_id = :jr"),
            {"jr": str(job_run_id)},
        )
        conn.execute(
            text("DELETE FROM tayfin_ingestor.instruments WHERE created_by_job_run_id = :jr"),
            {"jr": str(job_run_id)},
        )
        conn.execute(
            text("DELETE FROM tayfin_ingestor.job_runs WHERE id = :jr"),
            {"jr": str(job_run_id)},
        )


@pytest.fixture(scope="module")
def client(seed):
    """Flask test client with seed data already in the DB."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
