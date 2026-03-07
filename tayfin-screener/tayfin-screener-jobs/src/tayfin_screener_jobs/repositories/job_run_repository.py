"""Shared audit repository — job_runs table."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"


class JobRunRepository:
    """Persist and finalize job_run audit records."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(
        self,
        job_name: str,
        trigger_type: str = "cli",
        config: dict | None = None,
    ) -> UUID:
        """Insert a new job_run and return its id."""
        sql = text(f"""
            INSERT INTO {SCHEMA}.job_runs
                (job_name, trigger_type, status, started_at, config)
            VALUES
                (:job_name, :trigger_type, 'RUNNING', :started_at, CAST(:config AS jsonb))
            RETURNING id
        """)
        import json

        with self._engine.begin() as conn:
            row = conn.execute(
                sql,
                {
                    "job_name": job_name,
                    "trigger_type": trigger_type,
                    "started_at": datetime.now(timezone.utc),
                    "config": json.dumps(config) if config else None,
                },
            ).fetchone()
        job_run_id = row[0]
        logger.info("Created job_run %s for %s", job_run_id, job_name)
        return job_run_id

    def finalize(
        self,
        job_run_id: UUID,
        status: str,
        items_total: int = 0,
        items_succeeded: int = 0,
        items_failed: int = 0,
        error_summary: str | None = None,
    ) -> None:
        """Mark a job_run as completed or failed."""
        sql = text(f"""
            UPDATE {SCHEMA}.job_runs
            SET status = :status,
                finished_at = :finished_at,
                items_total = :items_total,
                items_succeeded = :items_succeeded,
                items_failed = :items_failed,
                error_summary = :error_summary,
                updated_at = now()
            WHERE id = :id
        """)
        with self._engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "id": str(job_run_id),
                    "status": status,
                    "finished_at": datetime.now(timezone.utc),
                    "items_total": items_total,
                    "items_succeeded": items_succeeded,
                    "items_failed": items_failed,
                    "error_summary": error_summary,
                },
            )
        logger.info("Finalized job_run %s → %s", job_run_id, status)
