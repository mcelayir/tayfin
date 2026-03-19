"""Regression tests for DB cleanup helpers."""
from datetime import date

import pytest
from sqlalchemy import text

from .db_utils import delete_rows_by_job_run


def _insert_job_run(conn):
    res = conn.execute(
        text(
            "INSERT INTO tayfin_ingestor.job_runs (job_name, trigger_type, status, started_at, finished_at) "
            "VALUES ('test-cleanup', 'test', 'COMPLETED', now(), now()) RETURNING id"
        )
    )
    return res.scalar()


def test_delete_rows_by_job_run_removes_test_rows(db_engine):
    engine = db_engine

    with engine.begin() as conn:
        jr = _insert_job_run(conn)

        # insert an instrument
        conn.execute(
            text(
                "INSERT INTO tayfin_ingestor.instruments (ticker, country, created_by_job_run_id) "
                "VALUES ('ZZTEST', 'US', :jr)"
            ),
            {"jr": str(jr)},
        )

        # insert OHLCV row for that instrument (minimal fields)
        instr_id = conn.execute(
            text(
                "SELECT id FROM tayfin_ingestor.instruments WHERE ticker = 'ZZTEST' AND country = 'US'"
            )
        ).scalar()

        conn.execute(
            text(
                "INSERT INTO tayfin_ingestor.ohlcv_daily (instrument_id, as_of_date, open, high, low, close, volume, source, created_by_job_run_id) "
                "VALUES (:iid, :d, 1, 1, 1, 1, 1, 'test', :jr)"
            ),
            {"iid": str(instr_id), "d": date(2099, 1, 1), "jr": str(jr)},
        )

    # run cleanup helper
    delete_rows_by_job_run(engine, jr, schema="tayfin_ingestor")

    # verify rows removed
    with engine.begin() as conn:
        inst = conn.execute(
            text("SELECT id FROM tayfin_ingestor.instruments WHERE ticker = 'ZZTEST' AND country = 'US'")
        ).fetchone()
        assert inst is None

        ohlcv = conn.execute(
            text("SELECT id FROM tayfin_ingestor.ohlcv_daily WHERE created_by_job_run_id = :jr"),
            {"jr": str(jr)},
        ).fetchone()
        assert ohlcv is None

        # remove job_runs row
        conn.execute(text("DELETE FROM tayfin_ingestor.job_runs WHERE id = :jr"), {"jr": str(jr)})
