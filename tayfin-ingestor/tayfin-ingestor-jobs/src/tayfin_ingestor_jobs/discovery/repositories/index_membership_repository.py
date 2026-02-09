from sqlalchemy import text


class IndexMembershipRepository:
    def __init__(self, engine):
        self.engine = engine

    def upsert(self, index_code: str, instrument_id: str, country: str, effective_date: str | None, created_by_job_run_id: str, updated_by_job_run_id: str | None = None) -> str:
        stmt = text(
            """
            INSERT INTO tayfin_ingestor.index_memberships (index_code, instrument_id, country, effective_date, created_at, updated_at, created_by_job_run_id, updated_by_job_run_id)
            VALUES (:index_code, :instrument_id, :country, :effective_date, now(), now(), :created_by_job_run_id, :updated_by_job_run_id)
            ON CONFLICT (index_code, instrument_id) DO UPDATE SET country = EXCLUDED.country, effective_date = EXCLUDED.effective_date, updated_at = now(), updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"index_code": index_code, "instrument_id": instrument_id, "country": country, "effective_date": effective_date, "created_by_job_run_id": created_by_job_run_id, "updated_by_job_run_id": updated_by_job_run_id})
            row = res.fetchone()
            return str(row[0])
