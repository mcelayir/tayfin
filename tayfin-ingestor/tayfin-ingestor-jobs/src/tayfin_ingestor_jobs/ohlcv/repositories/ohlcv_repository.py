"""Repository for tayfin_ingestor.ohlcv_daily — idempotent upsert."""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)


class OhlcvRepository:
    """Upsert daily OHLCV rows into ``tayfin_ingestor.ohlcv_daily``.

    Conflict key: ``(instrument_id, as_of_date)``
    On conflict: overwrite open/high/low/close/volume/source and audit fields.
    """

    def __init__(self, engine):
        self.engine = engine

    def upsert_bulk(
        self,
        instrument_id: str,
        df: pd.DataFrame,
        source: str,
        job_run_id: str,
    ) -> int:
        """Upsert a normalized OHLCV DataFrame for a single instrument.

        Parameters
        ----------
        instrument_id : str
            UUID of the instrument.
        df : pd.DataFrame
            Must contain columns: as_of_date, open, high, low, close, volume.
        source : str
            Data source label (e.g. ``tradingview``, ``yfinance``).
        job_run_id : str
            UUID of the current job run.

        Returns
        -------
        int
            Number of rows upserted.
        """
        if df.empty:
            return 0

        stmt = text("""
            INSERT INTO tayfin_ingestor.ohlcv_daily
                (instrument_id, as_of_date, open, high, low, close, volume,
                 source, created_at, updated_at,
                 created_by_job_run_id, updated_by_job_run_id)
            VALUES
                (:instrument_id, :as_of_date, :open, :high, :low, :close, :volume,
                 :source, now(), now(),
                 :job_run_id, :job_run_id)
            ON CONFLICT (instrument_id, as_of_date) DO UPDATE SET
                open   = EXCLUDED.open,
                high   = EXCLUDED.high,
                low    = EXCLUDED.low,
                close  = EXCLUDED.close,
                volume = EXCLUDED.volume,
                source = EXCLUDED.source,
                updated_at = now(),
                updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
        """)

        rows = df.to_dict(orient="records")
        params = [
            {
                "instrument_id": instrument_id,
                "as_of_date": r["as_of_date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["volume"]),
                "source": source,
                "job_run_id": job_run_id,
            }
            for r in rows
        ]

        with self.engine.begin() as conn:
            conn.execute(stmt, params)

        logger.info(
            "ohlcv upserted %d rows for instrument=%s source=%s",
            len(params), instrument_id, source,
        )
        return len(params)
