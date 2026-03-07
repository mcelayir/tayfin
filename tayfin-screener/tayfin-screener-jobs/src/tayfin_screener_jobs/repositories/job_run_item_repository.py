"""Shared audit repository — job_run_items table."""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"


class JobRunItemRepository:
    """Persist per-item audit records within a job run."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(
        self,
        job_run_id: UUID,
        item_key: str,
        status: str,
        error_summary: str | None = None,
        error_details: dict | None = None,
    ) -> UUID:
        """Insert a job_run_item and return its id."""
        import json

        sql = text(f"""
            INSERT INTO {SCHEMA}.job_run_items
                (job_run_id, item_key, status, error_summary, error_details)
            VALUES
                (:job_run_id, :item_key, :status, :error_summary, :error_details::jsonb)
            ON CONFLICT (job_run_id, item_key) DO UPDATE
                SET status = EXCLUDED.status,
                    error_summary = EXCLUDED.error_summary,
                    error_details = EXCLUDED.error_details,
                    updated_at = now()
            RETURNING id
        """)
        with self._engine.begin() as conn:
            row = conn.execute(
                sql,
                {
                    "job_run_id": str(job_run_id),
                    "item_key": item_key,
                    "status": status,
                    "error_summary": error_summary,
                    "error_details": json.dumps(error_details) if error_details else None,
                },
            ).fetchone()
        return row[0]
