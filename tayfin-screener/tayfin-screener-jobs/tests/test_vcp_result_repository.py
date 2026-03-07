"""Tests for VcpResultRepository — idempotent upsert behaviour."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from tayfin_screener_jobs.vcp.repositories.vcp_result_repository import (
    VcpResultRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_job_run_id() -> str:
    return str(uuid.uuid4())


def _make_row(
    ticker: str = "AAPL",
    as_of_date: date | str = "2026-03-07",
    vcp_score: float = 65.0,
    vcp_confidence: float | None = 0.72,
    pattern_detected: bool = True,
    features: dict | None = None,
    job_run_id: str | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "vcp_score": vcp_score,
        "vcp_confidence": vcp_confidence,
        "pattern_detected": pattern_detected,
        "features_json": features or {
            "contractions": [0.25, 0.14, 0.08],
            "atr_trend": -0.18,
            "volume_dryup": True,
            "near_52w_high": True,
            "ma_alignment": True,
        },
        "created_by_job_run_id": job_run_id or _fake_job_run_id(),
    }


# ---------------------------------------------------------------------------
# Unit tests — verify SQL generation and chunking logic
# ---------------------------------------------------------------------------

class TestUpsertEmpty:
    """Calling upsert with an empty list should be a no-op."""

    def test_empty_list_returns_zero(self):
        engine = MagicMock()
        repo = VcpResultRepository(engine)
        assert repo.upsert([]) == 0
        engine.begin.assert_not_called()


class TestUpsertSQLShape:
    """Verify the SQL statement contains correct columns and ON CONFLICT."""

    def test_single_row_executes_insert(self):
        """A single-row upsert should execute one INSERT … ON CONFLICT."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        row = _make_row()
        affected = repo.upsert([row])

        assert affected == 1
        engine.begin.assert_called_once()
        call_args = mock_conn.execute.call_args
        sql_text = str(call_args[0][0])

        # Verify key SQL fragments
        assert "INSERT INTO tayfin_screener.vcp_results" in sql_text
        assert "ON CONFLICT (ticker, as_of_date)" in sql_text
        assert "DO UPDATE SET" in sql_text
        assert "vcp_score" in sql_text
        assert "features_json" in sql_text
        assert "updated_by_job_run_id" in sql_text

    def test_batch_of_five(self):
        """A 5-row upsert should produce 5 value tuples."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        jid = _fake_job_run_id()
        rows = [
            _make_row(ticker=f"T{i}", as_of_date=f"2026-03-0{i+1}", job_run_id=jid)
            for i in range(5)
        ]
        affected = repo.upsert(rows)

        assert affected == 5
        call_args = mock_conn.execute.call_args
        bind_params = call_args[0][1]
        # Should have bind params for all 5 rows
        assert "ticker_0" in bind_params
        assert "ticker_4" in bind_params
        assert bind_params["ticker_0"] == "T0"
        assert bind_params["ticker_4"] == "T4"


class TestUpsertChunking:
    """Verify large batches are split into chunks."""

    def test_chunking(self):
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 500
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        jid = _fake_job_run_id()
        rows = [
            _make_row(ticker=f"T{i}", as_of_date="2026-01-01", job_run_id=jid)
            for i in range(1200)
        ]
        affected = repo.upsert(rows)

        # 1200 rows / 500 chunk size = 3 chunks
        assert mock_conn.execute.call_count == 3
        # 500 + 500 + 500 (mocked) = 1500, but real would be 500+500+200
        assert affected == 1500  # mocked rowcount × 3


class TestUpsertFieldMapping:
    """Verify individual field values are mapped correctly into bind params."""

    def test_features_json_dict_serialized(self):
        """features_json as dict should be JSON-serialized."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        features = {"contractions": [0.25, 0.14], "ma_alignment": True}
        row = _make_row(features=features)
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        # Should be JSON string, sorted keys
        parsed = json.loads(bind["features_json_0"])
        assert parsed == {"contractions": [0.25, 0.14], "ma_alignment": True}

    def test_features_json_string_passthrough(self):
        """features_json already a string should pass through."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        json_str = '{"key": "value"}'
        row = _make_row(features=json_str)  # type: ignore[arg-type]
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert bind["features_json_0"] == json_str

    def test_nullable_confidence(self):
        """vcp_confidence=None should be passed as None."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        row = _make_row(vcp_confidence=None)
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert bind["vcp_confidence_0"] is None

    def test_pattern_detected_bool(self):
        """pattern_detected should be stored as a Python bool."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        engine = MagicMock()
        engine.begin.return_value = mock_conn

        repo = VcpResultRepository(engine)
        row = _make_row(pattern_detected=False)
        repo.upsert([row])

        bind = mock_conn.execute.call_args[0][1]
        assert bind["pattern_detected_0"] is False
