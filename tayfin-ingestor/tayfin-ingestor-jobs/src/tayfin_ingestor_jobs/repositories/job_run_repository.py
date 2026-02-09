from datetime import datetime
from sqlalchemy import text


class JobRunRepository:
    def __init__(self, engine):
        self.engine = engine

    def create(self, job_name: str, trigger_type: str = "MANUAL_CLI") -> str:
        now = datetime.utcnow()
        stmt = text(
            """
            INSERT INTO tayfin_ingestor.job_runs (job_name, trigger_type, status, started_at, items_total, items_succeeded, items_failed, created_at, updated_at)
            VALUES (:job_name, :trigger_type, 'RUNNING', :started_at, 0, 0, 0, :created_at, :updated_at)
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            res = conn.execute(
                stmt,
                {
                    "job_name": job_name,
                    "trigger_type": trigger_type,
                    "started_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            row = res.fetchone()
            return str(row[0])

    def finalize(self, job_run_id: str, status: str, items_total: int, items_succeeded: int, items_failed: int, error_summary: str | None = None, error_details: dict | None = None):
        stmt = text(
            """
            UPDATE tayfin_ingestor.job_runs
            SET status = :status, finished_at = now(), items_total = :items_total, items_succeeded = :items_succeeded, items_failed = :items_failed, error_summary = :error_summary, error_details = :error_details, updated_at = now()
            WHERE id = :id
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "status": status,
                    "items_total": items_total,
                    "items_succeeded": items_succeeded,
                    "items_failed": items_failed,
                    "error_summary": error_summary,
                    "error_details": error_details,
                    "id": job_run_id,
                },
            )
