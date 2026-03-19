"""Database cleanup utilities for tests.

Helpers here delete only rows that were created during tests by using the
`created_by_job_run_id` marker column. This preserves baseline objects and
data applied by Flyway migrations.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def delete_rows_by_job_run(engine: Engine, job_run_id: str, schema: str = "tayfin_ingestor") -> None:
    """Delete rows from all tables in `schema` that have a
    `created_by_job_run_id` column and match the provided `job_run_id`.

    This function queries information_schema to find tables with the
    `created_by_job_run_id` column, and issues DELETE statements for each
    matching table. Using this approach avoids truncating baseline tables
    that were created by Flyway migrations (which do not set this column).
    """
    if not job_run_id:
        return

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = :schema AND column_name = 'created_by_job_run_id'"
            ),
            {"schema": schema},
        ).fetchall()

        for (table_name,) in rows:
            # Use parameterized query for safety
            conn.execute(
                text(f"DELETE FROM {schema}.\"{table_name}\" WHERE created_by_job_run_id = :jr"),
                {"jr": str(job_run_id)},
            )
