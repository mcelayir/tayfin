"""Repository for tayfin_indicator.indicator_series table."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from sqlalchemy import text


class IndicatorSeriesRepository:
    """Upsert-oriented access to tayfin_indicator.indicator_series."""

    CHUNK_SIZE = 1000

    def __init__(self, engine):
        self.engine = engine

    # ------------------------------------------------------------------
    # Read helpers (same-context DB access — §1.1 allows this)
    # ------------------------------------------------------------------

    def get_series(
        self,
        ticker: str,
        indicator_key: str,
        params_json: dict,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[dict]:
        """Return indicator rows for a single ticker, ordered by as_of_date.

        Each returned dict has keys: ``as_of_date``, ``value``.

        Used by derived-indicator jobs (e.g. sma_slope reads sma values)
        that need same-context data without making a network hop.
        """
        pj = json.dumps(params_json, sort_keys=True)
        clauses = [
            "ticker = :ticker",
            "indicator_key = :indicator_key",
            "params_json = CAST(:params_json AS jsonb)",
        ]
        bind: dict = {
            "ticker": ticker,
            "indicator_key": indicator_key,
            "params_json": pj,
        }
        if from_date is not None:
            clauses.append("as_of_date >= :from_date")
            bind["from_date"] = from_date
        if to_date is not None:
            clauses.append("as_of_date <= :to_date")
            bind["to_date"] = to_date

        where = " AND ".join(clauses)
        stmt = text(
            f"""
            SELECT as_of_date, value
            FROM tayfin_indicator.indicator_series
            WHERE {where}
            ORDER BY as_of_date
            """
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, bind).mappings().all()
            return [{"as_of_date": r["as_of_date"], "value": float(r["value"])} for r in rows]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_indicator_rows(self, rows: list[dict]) -> int:
        """Upsert *rows* in chunks; return total rows affected.

        Each dict must contain:
            ticker, as_of_date, indicator_key, params_json (dict),
            value, source, created_by_job_run_id

        ON CONFLICT updates: value, updated_at, updated_by_job_run_id.
        """
        if not rows:
            return 0

        total = 0
        for start in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[start : start + self.CHUNK_SIZE]
            total += self._upsert_chunk(chunk)
        return total

    # ------------------------------------------------------------------

    def _upsert_chunk(self, chunk: list[dict]) -> int:
        """Insert a single chunk with ON CONFLICT upsert."""
        now = datetime.now(timezone.utc)

        # Build VALUES placeholders  (:ticker_0, :as_of_date_0, …)
        placeholders = []
        bind: dict = {}
        for i, row in enumerate(chunk):
            ph = (
                f"(:ticker_{i}, :as_of_date_{i}, :indicator_key_{i}, "
                f"CAST(:params_json_{i} AS jsonb), :value_{i}, :source_{i}, "
                f":created_at_{i}, :updated_at_{i}, :created_by_{i}, :updated_by_{i})"
            )
            placeholders.append(ph)
            params_j = row["params_json"]
            if isinstance(params_j, dict):
                params_j = json.dumps(params_j, sort_keys=True)
            bind[f"ticker_{i}"] = row["ticker"]
            bind[f"as_of_date_{i}"] = row["as_of_date"]
            bind[f"indicator_key_{i}"] = row["indicator_key"]
            bind[f"params_json_{i}"] = params_j
            bind[f"value_{i}"] = float(row["value"])
            bind[f"source_{i}"] = row.get("source", "computed")
            bind[f"created_at_{i}"] = now
            bind[f"updated_at_{i}"] = now
            bind[f"created_by_{i}"] = row["created_by_job_run_id"]
            bind[f"updated_by_{i}"] = row.get("updated_by_job_run_id")

        values_sql = ",\n".join(placeholders)
        stmt = text(
            f"""
            INSERT INTO tayfin_indicator.indicator_series
                (ticker, as_of_date, indicator_key, params_json,
                 value, source,
                 created_at, updated_at,
                 created_by_job_run_id, updated_by_job_run_id)
            VALUES
                {values_sql}
            ON CONFLICT (ticker, as_of_date, indicator_key, params_json)
            DO UPDATE SET
                value                 = EXCLUDED.value,
                updated_at            = EXCLUDED.updated_at,
                updated_by_job_run_id = EXCLUDED.created_by_job_run_id
            """
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt, bind)
            return result.rowcount
