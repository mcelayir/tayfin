"""Repository for tayfin_screener.mcsa_results table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA = "tayfin_screener"
TABLE = f"{SCHEMA}.mcsa_results"
CHUNK_SIZE = 500


class McsaResultRepository:
    """Upsert-oriented access to tayfin_screener.mcsa_results.

    Natural key: (ticker, as_of_date).
    On conflict the row is updated with new scores, band, evidence,
    missing_fields, updated_by_job_run_id, and updated_at.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(self, rows: list[dict]) -> int:
        """Upsert *rows* in chunks; return total rows affected.

        Each dict must contain:
            ticker, as_of_date, mcsa_score, mcsa_band,
            trend_score, vcp_component, volume_score, fundamental_score,
            evidence_json (dict), missing_fields (list),
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
                f":mcsa_score_{i}, :mcsa_band_{i}, "
                f":trend_score_{i}, :vcp_component_{i}, "
                f":volume_score_{i}, :fundamental_score_{i}, "
                f"CAST(:evidence_json_{i} AS jsonb), "
                f"CAST(:missing_fields_{i} AS jsonb), "
                f":created_at_{i}, :updated_at_{i}, "
                f":created_by_{i}, :updated_by_{i})"
            )
            placeholders.append(ph)

            evidence = row["evidence_json"]
            if isinstance(evidence, dict):
                evidence = json.dumps(evidence, sort_keys=True)

            missing = row.get("missing_fields", [])
            if isinstance(missing, list):
                missing = json.dumps(missing)

            bind[f"ticker_{i}"] = row["ticker"]
            bind[f"instrument_id_{i}"] = row.get("instrument_id")
            bind[f"as_of_date_{i}"] = row["as_of_date"]
            bind[f"mcsa_score_{i}"] = float(row["mcsa_score"])
            bind[f"mcsa_band_{i}"] = row["mcsa_band"]
            bind[f"trend_score_{i}"] = float(row["trend_score"])
            bind[f"vcp_component_{i}"] = float(row["vcp_component"])
            bind[f"volume_score_{i}"] = float(row["volume_score"])
            bind[f"fundamental_score_{i}"] = float(row["fundamental_score"])
            bind[f"evidence_json_{i}"] = evidence
            bind[f"missing_fields_{i}"] = missing
            bind[f"created_at_{i}"] = now
            bind[f"updated_at_{i}"] = now
            bind[f"created_by_{i}"] = row["created_by_job_run_id"]
            bind[f"updated_by_{i}"] = row.get("updated_by_job_run_id") or row["created_by_job_run_id"]

        values_sql = ",\n".join(placeholders)

        stmt = text(f"""
            INSERT INTO {TABLE}
                (ticker, instrument_id, as_of_date,
                 mcsa_score, mcsa_band,
                 trend_score, vcp_component,
                 volume_score, fundamental_score,
                 evidence_json, missing_fields,
                 created_at, updated_at,
                 created_by_job_run_id, updated_by_job_run_id)
            VALUES
                {values_sql}
            ON CONFLICT (ticker, as_of_date)
            DO UPDATE SET
                mcsa_score            = EXCLUDED.mcsa_score,
                mcsa_band             = EXCLUDED.mcsa_band,
                trend_score           = EXCLUDED.trend_score,
                vcp_component         = EXCLUDED.vcp_component,
                volume_score          = EXCLUDED.volume_score,
                fundamental_score     = EXCLUDED.fundamental_score,
                evidence_json         = EXCLUDED.evidence_json,
                missing_fields        = EXCLUDED.missing_fields,
                instrument_id         = EXCLUDED.instrument_id,
                updated_at            = EXCLUDED.updated_at,
                updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
        """)

        with self._engine.begin() as conn:
            result = conn.execute(stmt, bind)
            affected = result.rowcount
            logger.debug("Upserted %d mcsa_results rows", affected)
            return affected
