"""Repository for tayfin_screener.vcp_results table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"
TABLE = f"{SCHEMA}.vcp_results"
CHUNK_SIZE = 500


class VcpResultRepository:
    """Upsert-oriented access to tayfin_screener.vcp_results.

    Natural key: (ticker, as_of_date).
    On conflict the row is updated with new score, confidence, features,
    pattern_detected, updated_by_job_run_id, and updated_at.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(self, rows: list[dict]) -> int:
        """Upsert *rows* in chunks; return total rows affected.

        Each dict must contain:
            ticker, as_of_date, vcp_score, vcp_confidence,
            pattern_detected, features_json (dict),
            created_by_job_run_id

        Optional:
            instrument_id, updated_by_job_run_id
        """
        if not rows:
            return 0

        total = 0
        for start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[start : start + CHUNK_SIZE]
            total += self._upsert_chunk(chunk)
        return total

    # ------------------------------------------------------------------

    def _upsert_chunk(self, chunk: list[dict]) -> int:
        """Insert a single chunk with ON CONFLICT upsert."""
        now = datetime.now(timezone.utc)

        placeholders: list[str] = []
        bind: dict = {}

        for i, row in enumerate(chunk):
            ph = (
                f"(:ticker_{i}, :instrument_id_{i}, :as_of_date_{i}, "
                f":vcp_score_{i}, :vcp_confidence_{i}, :pattern_detected_{i}, "
                f"CAST(:features_json_{i} AS jsonb), "
                f":created_at_{i}, :updated_at_{i}, "
                f":created_by_{i}, :updated_by_{i})"
            )
            placeholders.append(ph)

            features = row["features_json"]
            if isinstance(features, dict):
                features = json.dumps(features, sort_keys=True)

            bind[f"ticker_{i}"] = row["ticker"]
            bind[f"instrument_id_{i}"] = row.get("instrument_id")
            bind[f"as_of_date_{i}"] = row["as_of_date"]
            bind[f"vcp_score_{i}"] = float(row["vcp_score"])
            bind[f"vcp_confidence_{i}"] = (
                float(row["vcp_confidence"]) if row.get("vcp_confidence") is not None else None
            )
            bind[f"pattern_detected_{i}"] = bool(row["pattern_detected"])
            bind[f"features_json_{i}"] = features
            bind[f"created_at_{i}"] = now
            bind[f"updated_at_{i}"] = now
            bind[f"created_by_{i}"] = row["created_by_job_run_id"]
            bind[f"updated_by_{i}"] = row.get("updated_by_job_run_id")

        values_sql = ",\n".join(placeholders)

        stmt = text(f"""
            INSERT INTO {TABLE}
                (ticker, instrument_id, as_of_date,
                 vcp_score, vcp_confidence, pattern_detected,
                 features_json,
                 created_at, updated_at,
                 created_by_job_run_id, updated_by_job_run_id)
            VALUES
                {values_sql}
            ON CONFLICT (ticker, as_of_date)
            DO UPDATE SET
                vcp_score             = EXCLUDED.vcp_score,
                vcp_confidence        = EXCLUDED.vcp_confidence,
                pattern_detected      = EXCLUDED.pattern_detected,
                features_json         = EXCLUDED.features_json,
                instrument_id         = EXCLUDED.instrument_id,
                updated_at            = EXCLUDED.updated_at,
                updated_by_job_run_id = EXCLUDED.created_by_job_run_id
        """)

        with self._engine.begin() as conn:
            result = conn.execute(stmt, bind)
            affected = result.rowcount
            logger.debug("Upserted %d vcp_results rows", affected)
            return affected
