from sqlalchemy import text


class InstrumentRepository:
    def __init__(self, engine):
        self.engine = engine

    def upsert(self, ticker: str, country: str, instrument_type: str | None, created_by_job_run_id: str, updated_by_job_run_id: str | None = None) -> str:
        stmt = text(
            """
            INSERT INTO tayfin_ingestor.instruments (ticker, country, instrument_type, created_at, updated_at, created_by_job_run_id, updated_by_job_run_id)
            VALUES (:ticker, :country, :instrument_type, now(), now(), :created_by_job_run_id, :updated_by_job_run_id)
            ON CONFLICT (ticker, country) DO UPDATE SET instrument_type = EXCLUDED.instrument_type, updated_at = now(), updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
            RETURNING id
            """
        )
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"ticker": ticker, "country": country, "instrument_type": instrument_type, "created_by_job_run_id": created_by_job_run_id, "updated_by_job_run_id": updated_by_job_run_id})
            row = res.fetchone()
            return str(row[0])
