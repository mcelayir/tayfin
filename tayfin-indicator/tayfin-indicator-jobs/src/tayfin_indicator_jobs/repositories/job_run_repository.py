"""Repository for tayfin_indicator.job_runs audit table."""

import json
from datetime import datetime, timezone

from sqlalchemy import text


class JobRunRepository:
    """CRUD operations on tayfin_indicator.job_runs."""

    def __init__(self, engine):
        self.engine = engine

    def create(
        self,
        job_name: str,
        target_name: str | None = None,
        status: str = "RUNNING",
        params: dict | None = None,
    ) -> str:
        """Insert a new job_run and return its id."""
        now = datetime.now(timezone.utc)
        stmt = text(
            """
            INSERT INTO tayfin_indicator.job_runs
                (job_name, target_name, status, started_at, params, created_at, updated_at)
            VALUES
                (:job_name, :target_name, :status, :started_at, :params, :created_at, :updated_at)
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                stmt,
                {
                    "job_name": job_name,
                    "target_name": target_name,
                    "status": status,
                    "started_at": now,
                    "params": json.dumps(params) if params else None,
                    "created_at": now,
                    "updated_at": now,
                },
            ).fetchone()
            return str(row[0])

    def finalize(
        self,
        job_run_id: str,
        status: str,
        message: str | None = None,
    ) -> None:
        """Mark a job_run as finished."""
        stmt = text(
            """
            UPDATE tayfin_indicator.job_runs
            SET status     = :status,
                finished_at = now(),
                message     = :message,
                updated_at  = now()
            WHERE id = :id
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {"status": status, "message": message, "id": job_run_id},
            )
