"""Repository for tayfin_screener.mcsa_results table.

Idempotent upsert on (ticker, as_of_date).  SQLAlchemy Core only.
Every write is linked to a ``job_run_id`` for provenance (§3.5).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"
TABLE = f"{SCHEMA}.mcsa_results"
CHUNK_SIZE = 500


class McsaResultRepository:
    """Upsert-oriented access to tayfin_screener.mcsa_results.

    Natural key: (ticker, as_of_date).
    On conflict the row is updated with new criteria, RS rank,
    pass status, updated_by_job_run_id, and updated_at.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(self, rows: list[dict]) -> int:
        """Upsert *rows* in chunks; return total rows affected.

        Each dict must contain:
            ticker, as_of_date, mcsa_pass, criteria_json (dict),
            rs_rank, criteria_count_pass, created_by_job_run_id

        Optional:
            instrument_id, updated_by_job_run_id
        """
        if not rows:
            return 0

        total = 0
        for start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[start : start + CHUNK_SIZE]
            total += self._upsert_chunk(chunk)
        return total

    # ------------------------------------------------------------------

    def _upsert_chunk(self, chunk: list[dict]) -> int:
        """Insert a single chunk with ON CONFLICT upsert."""
        now = datetime.now(timezone.utc)

        placeholders: list[str] = []
        bind: dict = {}

        for i, row in enumerate(chunk):
            ph = (
                f"(:ticker_{i}, :instrument_id_{i}, :as_of_date_{i}, "
                f":mcsa_pass_{i}, CAST(:criteria_json_{i} AS jsonb), "
                f":rs_rank_{i}, :criteria_count_pass_{i}, "
                f":created_at_{i}, :updated_at_{i}, "
                f":created_by_{i}, :updated_by_{i})"
            )
            placeholders.append(ph)

            criteria = row["criteria_json"]
            if isinstance(criteria, dict):
                criteria = json.dumps(criteria, sort_keys=True)

            bind[f"ticker_{i}"] = row["ticker"]
            bind[f"instrument_id_{i}"] = row.get("instrument_id")
            bind[f"as_of_date_{i}"] = row["as_of_date"]
            bind[f"mcsa_pass_{i}"] = bool(row["mcsa_pass"])
            bind[f"criteria_json_{i}"] = criteria
            bind[f"rs_rank_{i}"] = float(row["rs_rank"])
            bind[f"criteria_count_pass_{i}"] = int(row["criteria_count_pass"])
            bind[f"created_at_{i}"] = now
            bind[f"updated_at_{i}"] = now
            bind[f"created_by_{i}"] = row["created_by_job_run_id"]
            bind[f"updated_by_{i}"] = row.get("updated_by_job_run_id")

        values_sql = ",\n".join(placeholders)

        stmt = text(f"""
            INSERT INTO {TABLE}
                (ticker, instrument_id, as_of_date,
                 mcsa_pass, criteria_json,
                 rs_rank, criteria_count_pass,
                 created_at, updated_at,
                 created_by_job_run_id, updated_by_job_run_id)
            VALUES
                {values_sql}
            ON CONFLICT (ticker, as_of_date)
            DO UPDATE SET
                mcsa_pass             = EXCLUDED.mcsa_pass,
                criteria_json         = EXCLUDED.criteria_json,
                rs_rank               = EXCLUDED.rs_rank,
                criteria_count_pass   = EXCLUDED.criteria_count_pass,
                instrument_id         = EXCLUDED.instrument_id,
                updated_at            = EXCLUDED.updated_at,
                updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
        """)

        with self._engine.begin() as conn:
            result = conn.execute(stmt, bind)
            affected = result.rowcount
            logger.debug("Upserted %d mcsa_results rows", affected)
            return affected
