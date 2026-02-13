"""Repository for tayfin_indicator.job_run_items audit table."""

import json
from datetime import datetime, timezone

from sqlalchemy import text


class JobRunItemRepository:
    """CRUD operations on tayfin_indicator.job_run_items."""

    def __init__(self, engine):
        self.engine = engine

    def create(
        self,
        job_run_id: str,
        item_key: str,
        status: str = "SUCCESS",
        message: str | None = None,
        details: dict | None = None,
    ) -> str:
        """Insert a new job_run_item and return its id."""
        now = datetime.now(timezone.utc)
        stmt = text(
            """
            INSERT INTO tayfin_indicator.job_run_items
                (job_run_id, item_key, status, message, details, created_at, updated_at)
            VALUES
                (:job_run_id, :item_key, :status, :message, :details, :created_at, :updated_at)
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                stmt,
                {
                    "job_run_id": job_run_id,
                    "item_key": item_key,
                    "status": status,
                    "message": message,
                    "details": json.dumps(details) if details else None,
                    "created_at": now,
                    "updated_at": now,
                },
            ).fetchone()
            return str(row[0])
