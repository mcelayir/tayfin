from datetime import datetime
from sqlalchemy import text


class JobRunItemRepository:
    def __init__(self, engine):
        self.engine = engine

    def upsert(self, job_run_id: str, item_key: str, status: str, error_summary: str | None = None, error_details: dict | None = None):
        stmt = text(
            """
            INSERT INTO tayfin_ingestor.job_run_items (job_run_id, item_key, status, error_summary, error_details, created_at, updated_at)
            VALUES (:job_run_id, :item_key, :status, :error_summary, :error_details, now(), now())
            ON CONFLICT (job_run_id, item_key) DO UPDATE SET status = EXCLUDED.status, error_summary = EXCLUDED.error_summary, error_details = EXCLUDED.error_details, updated_at = now()
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"job_run_id": job_run_id, "item_key": item_key, "status": status, "error_summary": error_summary, "error_details": error_details})
            row = res.fetchone()
            return str(row[0])
