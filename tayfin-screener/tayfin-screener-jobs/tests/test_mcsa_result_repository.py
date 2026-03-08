"""Tests for McsaResultRepository — idempotent upsert behaviour."""

from __future__ import annotations

import json
import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from tayfin_screener_jobs.mcsa.repositories.mcsa_result_repository import (
    McsaResultRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_job_run_id() -> str:
    return str(uuid.uuid4())


def _make_row(
    ticker: str = "AAPL",
    as_of_date: date | str = "2026-03-07",
    mcsa_score: float = 72.0,
    mcsa_band: str = "watchlist",
    trend_score: float = 25.0,
    vcp_component: float = 28.0,
    volume_score: float = 10.0,
    fundamental_score: float = 9.0,
    evidence: dict | None = None,
    missing_fields: list | None = None,
    job_run_id: str | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "mcsa_score": mcsa_score,
        "mcsa_band": mcsa_band,
        "trend_score": trend_score,
        "vcp_component": vcp_component,
        "volume_score": volume_score,
        "fundamental_score": fundamental_score,
        "evidence_json": evidence or {
            "trend": {"score": 25.0},
            "vcp": {"score": 28.0},
            "volume": {"score": 10.0},
            "fundamentals": {"score": 9.0},
        },
        "missing_fields": missing_fields or [],
        "created_by_job_run_id": job_run_id or _fake_job_run_id(),
    }


def _mock_engine():
    """Return a mock engine + connection for upsert tests."""
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    engine = MagicMock()
    engine.begin.return_value = mock_conn
    return engine, mock_conn, mock_result


# ---------------------------------------------------------------------------
# Unit tests — verify SQL generation and chunking logic
# ---------------------------------------------------------------------------

class TestUpsertEmpty:
    """Calling upsert with an empty list should be a no-op."""

    def test_empty_list_returns_zero(self):
        engine = MagicMock()
        repo = McsaResultRepository(engine)
        assert repo.upsert([]) == 0
        engine.begin.assert_not_called()


class TestUpsertSQLShape:
    """Verify the SQL statement contains correct columns and ON CONFLICT."""

    def test_single_row_executes_insert(self):
        engine, mock_conn, mock_result = _mock_engine()
        mock_result.rowcount = 1

        repo = McsaResultRepository(engine)
        affected = repo.upsert([_make_row()])

        assert affected == 1
        engine.begin.assert_called_once()
        call_args = mock_conn.execute.call_args
        sql_text = str(call_args[0][0])

        assert "INSERT INTO tayfin_screener.mcsa_results" in sql_text
        assert "ON CONFLICT (ticker, as_of_date)" in sql_text
        assert "DO UPDATE SET" in sql_text
        assert "mcsa_score" in sql_text
        assert "mcsa_band" in sql_text
        assert "evidence_json" in sql_text
        assert "missing_fields" in sql_text
        assert "updated_by_job_run_id" in sql_text

    def test_batch_of_five(self):
        engine, mock_conn, mock_result = _mock_engine()
        mock_result.rowcount = 5

        repo = McsaResultRepository(engine)
        jid = _fake_job_run_id()
        rows = [
            _make_row(ticker=f"T{i}", as_of_date=f"2026-03-0{i+1}", job_run_id=jid)
            for i in range(5)
        ]
        affected = repo.upsert(rows)

        assert affected == 5
        call_args = mock_conn.execute.call_args
        bind_params = call_args[0][1]
        assert "ticker_0" in bind_params
        assert "ticker_4" in bind_params
        assert bind_params["ticker_0"] == "T0"
        assert bind_params["ticker_4"] == "T4"


class TestUpsertChunking:
    """Verify large batches are split into chunks."""

    def test_chunking(self):
        engine, mock_conn, mock_result = _mock_engine()
        mock_result.rowcount = 500

        repo = McsaResultRepository(engine)
        jid = _fake_job_run_id()
        rows = [
            _make_row(ticker=f"T{i}", as_of_date="2026-01-01", job_run_id=jid)
            for i in range(1200)
        ]
        affected = repo.upsert(rows)

        # 1200 rows / 500 chunk size = 3 chunks
        assert mock_conn.execute.call_count == 3
        assert affected == 1500  # mocked 500 × 3


class TestUpsertFieldMapping:
    """Verify field values mapped correctly into bind params."""

    def test_evidence_json_dict_serialized(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        evidence = {"trend": {"score": 25.0}, "total": 72.0}
        row = _make_row(evidence=evidence)
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        parsed = json.loads(bind["evidence_json_0"])
        assert parsed["trend"]["score"] == 25.0
        assert parsed["total"] == 72.0

    def test_evidence_json_string_passthrough(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        json_str = '{"key": "value"}'
        row = _make_row(evidence=json_str)  # type: ignore[arg-type]
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert bind["evidence_json_0"] == json_str

    def test_missing_fields_list_serialized(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        row = _make_row(missing_fields=["trend.sma_50", "vcp.vcp_score"])
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        parsed = json.loads(bind["missing_fields_0"])
        assert parsed == ["trend.sma_50", "vcp.vcp_score"]

    def test_mcsa_score_as_float(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        row = _make_row(mcsa_score=85)  # int input
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert isinstance(bind["mcsa_score_0"], float)
        assert bind["mcsa_score_0"] == 85.0

    def test_band_stored(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        row = _make_row(mcsa_band="strong")
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert bind["mcsa_band_0"] == "strong"

    def test_component_scores_as_floats(self):
        engine, mock_conn, _ = _mock_engine()
        repo = McsaResultRepository(engine)
        row = _make_row(
            trend_score=30, vcp_component=35,
            volume_score=15, fundamental_score=20,
        )
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert isinstance(bind["trend_score_0"], float)
        assert isinstance(bind["vcp_component_0"], float)
        assert isinstance(bind["volume_score_0"], float)
        assert isinstance(bind["fundamental_score_0"], float)
