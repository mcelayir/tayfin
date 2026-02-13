"""VolSmaComputeJob — compute volume SMA indicators and store in indicator_series.

For each ticker in the configured index:
1. Fetch OHLCV via ingestor API
2. Compute volume SMA windows from config
3. Upsert rows into indicator_series
4. Audit every ticker in job_run_items
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import date, timedelta

import pandas as pd
import typer

from ..clients.ingestor_client import IngestorClient
from ..db.engine import get_engine
from ..indicator.compute import compute_vol_sma
from ..repositories.indicator_series_repository import IndicatorSeriesRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..repositories.job_run_repository import JobRunRepository


class VolSmaComputeJob:
    """Compute volume SMA indicators for a given target index."""

    def __init__(self, target_name: str, target_cfg: dict, full_cfg: dict):
        self.target_name = target_name
        self.target_cfg = target_cfg
        self.full_cfg = full_cfg
        self.engine = get_engine()
        self.job_run_repo = JobRunRepository(self.engine)
        self.job_run_item_repo = JobRunItemRepository(self.engine)
        self.indicator_repo = IndicatorSeriesRepository(self.engine)
        self.ingestor = IngestorClient()

    @classmethod
    def from_config(cls, target_name: str, target_cfg: dict, full_cfg: dict) -> "VolSmaComputeJob":
        return cls(target_name=target_name, target_cfg=target_cfg, full_cfg=full_cfg)

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self, ticker: str | None = None, limit: int | None = None) -> None:
        indicators = self.target_cfg.get("indicators", [])
        index_code = self.target_cfg.get("index_code", "")
        lookback_days = int(os.environ.get("TAYFIN_INDICATOR_LOOKBACK_DAYS", "420"))

        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Extract vol_sma windows from config
        vol_sma_windows: list[int] = []
        for ind in indicators:
            if ind.get("key") == "vol_sma":
                w = ind.get("params", {}).get("window")
                if w:
                    vol_sma_windows.append(int(w))

        # Params snapshot for audit
        params = {
            "target_name": self.target_name,
            "index_code": index_code,
            "country": self.target_cfg.get("country"),
            "indicators": indicators,
            "lookback_days": lookback_days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "cli_overrides": {"ticker": ticker, "limit": limit},
        }

        job_run_id = self.job_run_repo.create(
            job_name="vol_sma_compute",
            target_name=self.target_name,
            status="RUNNING",
            params=params,
        )

        typer.echo(f"[vol_sma_compute] job_run_id  = {job_run_id}")
        typer.echo(f"[vol_sma_compute] target      = {self.target_name}")
        typer.echo(f"[vol_sma_compute] index_code  = {index_code}")
        typer.echo(f"[vol_sma_compute] date range  = {start_date} → {end_date}")

        # Resolve tickers
        instruments = self.ingestor.get_index_instruments(index_code)
        tickers = [i.get("ticker", i.get("symbol", "")) for i in instruments]
        if ticker:
            tickers = [t for t in tickers if t == ticker.upper()]
        if limit:
            tickers = tickers[:limit]
        typer.echo(f"[vol_sma_compute] tickers     = {len(tickers)}")
        typer.echo(f"[vol_sma_compute] vol_sma windows = {vol_sma_windows}")

        # Process each ticker (continue-on-failure)
        summary_rows: list[dict] = []

        for tkr in tickers:
            result = self._process_ticker(
                tkr, vol_sma_windows, start_date, end_date, job_run_id,
            )
            summary_rows.append(result)

            # Audit item
            self.job_run_item_repo.create(
                job_run_id=job_run_id,
                item_key=tkr,
                status=result["status"],
                message=result.get("error"),
                details={
                    "windows": vol_sma_windows,
                    "candles_fetched": result["candles_fetched"],
                    "rows_written": result["rows_written"],
                    "min_date": result["min_date"],
                    "max_date": result["max_date"],
                },
            )

        # Print summary table
        df = pd.DataFrame(summary_rows)
        typer.echo("\n" + df.to_string(index=False))

        succeeded = sum(1 for r in summary_rows if r["status"] == "SUCCESS")
        failed = len(summary_rows) - succeeded
        total_rows = sum(r["rows_written"] for r in summary_rows)

        typer.echo(
            f"\nTotal: {len(summary_rows)}  Succeeded: {succeeded}  "
            f"Failed: {failed}  Rows written: {total_rows}"
        )

        final_status = "SUCCESS" if failed == 0 else "FAILED"
        self.job_run_repo.finalize(
            job_run_id=job_run_id,
            status=final_status,
            message=(
                f"{succeeded}/{len(summary_rows)} tickers OK, "
                f"{total_rows} rows written"
            ),
        )
        typer.echo(f"[vol_sma_compute] status = {final_status}")

    # ------------------------------------------------------------------
    # Per-ticker processing
    # ------------------------------------------------------------------

    def _process_ticker(
        self,
        tkr: str,
        vol_sma_windows: list[int],
        start_date: date,
        end_date: date,
        job_run_id: str,
    ) -> dict:
        """Fetch OHLCV, compute volume SMA, upsert rows. Returns summary dict."""
        result: dict = {
            "ticker": tkr,
            "status": "SUCCESS",
            "candles_fetched": 0,
            "rows_written": 0,
            "min_date": "",
            "max_date": "",
            "error": "",
        }
        try:
            candles = self.ingestor.get_ohlcv_range(tkr, start_date, end_date)
            result["candles_fetched"] = len(candles)

            if not candles:
                result["status"] = "SUCCESS"
                result["error"] = "no candles"
                return result

            # Build a sorted DataFrame
            df = pd.DataFrame(candles)
            df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date
            df = df.sort_values("as_of_date").reset_index(drop=True)

            # Validate volume column exists and has no nulls
            if "volume" not in df.columns:
                result["status"] = "FAILED"
                result["error"] = "missing volume column in OHLCV data"
                return result

            volume = pd.to_numeric(df["volume"], errors="coerce")
            if volume.isna().any():
                result["status"] = "FAILED"
                result["error"] = "NULL/missing volume values detected"
                return result

            if (volume < 0).any():
                result["status"] = "FAILED"
                result["error"] = "negative volume values detected"
                return result

            rows_to_upsert: list[dict] = []

            for window in vol_sma_windows:
                if len(df) < window:
                    continue
                vol_sma_series = compute_vol_sma(volume, window)
                params_json = json.dumps({"window": window}, sort_keys=True)

                for idx in range(window - 1, len(df)):
                    val = vol_sma_series.iloc[idx]
                    if pd.isna(val):
                        continue
                    rows_to_upsert.append(
                        {
                            "ticker": tkr,
                            "as_of_date": df["as_of_date"].iloc[idx],
                            "indicator_key": "vol_sma",
                            "params_json": params_json,
                            "value": round(float(val), 4),
                            "source": "computed",
                            "created_by_job_run_id": job_run_id,
                        }
                    )

            if rows_to_upsert:
                written = self.indicator_repo.upsert_indicator_rows(rows_to_upsert)
                result["rows_written"] = written
                dates = [r["as_of_date"] for r in rows_to_upsert]
                result["min_date"] = str(min(dates))
                result["max_date"] = str(max(dates))

        except Exception as exc:
            result["status"] = "FAILED"
            result["error"] = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()

        return result
