"""SmaSlopeComputeJob — compute SMA slope and store in indicator_series.

Unlike other indicator jobs, this job reads **existing indicator data**
(SMA values) from the same context's database — not from the Ingestor API.
This is architecturally legal (§1.1 same-context DB read) and avoids an
unnecessary network hop to our own API.

For each ticker in the configured index:
1. Read SMA values from IndicatorSeriesRepository (direct DB read)
2. Compute slope: (sma_today - sma_N_days_ago) / sma_N_days_ago
3. Upsert rows into indicator_series
4. Audit every ticker in job_run_items

DEPENDENCY: ma_compute must run first (SMA-200 data must exist).
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
from ..indicator.compute import compute_sma_slope
from ..repositories.indicator_series_repository import IndicatorSeriesRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..repositories.job_run_repository import JobRunRepository


class SmaSlopeComputeJob:
    """Compute SMA slope indicators for a given target index.

    Reads precomputed SMA values from the indicator_series table
    (same-context DB read) and computes the slope over a configurable
    period.
    """

    DEFAULT_LOOKBACK_DAYS = 800

    def __init__(self, target_name: str, target_cfg: dict, full_cfg: dict):
        self.target_name = target_name
        self.target_cfg = target_cfg
        self.full_cfg = full_cfg
        self.engine = get_engine()
        self.job_run_repo = JobRunRepository(self.engine)
        self.job_run_item_repo = JobRunItemRepository(self.engine)
        self.indicator_repo = IndicatorSeriesRepository(self.engine)
        # Ingestor client used only for resolving index members
        self.ingestor = IngestorClient()

    @classmethod
    def from_config(cls, target_name: str, target_cfg: dict, full_cfg: dict) -> "SmaSlopeComputeJob":
        return cls(target_name=target_name, target_cfg=target_cfg, full_cfg=full_cfg)

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def run(self, ticker: str | None = None, limit: int | None = None) -> None:
        indicators = self.target_cfg.get("indicators", [])
        index_code = self.target_cfg.get("index_code", "")
        lookback_days = int(
            os.environ.get("TAYFIN_INDICATOR_LOOKBACK_DAYS", str(self.DEFAULT_LOOKBACK_DAYS))
        )

        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Extract sma_slope configs from indicators list
        slope_configs: list[dict] = []
        for ind in indicators:
            if ind.get("key") == "sma_slope":
                params = ind.get("params", {})
                sma_window = int(params.get("sma_window", 200))
                slope_period = int(params.get("slope_period", 20))
                slope_configs.append(
                    {"sma_window": sma_window, "slope_period": slope_period}
                )

        # Params snapshot for audit
        params_snapshot = {
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
            job_name="sma_slope_compute",
            target_name=self.target_name,
            status="RUNNING",
            params=params_snapshot,
        )

        typer.echo(f"[sma_slope_compute] job_run_id  = {job_run_id}")
        typer.echo(f"[sma_slope_compute] target      = {self.target_name}")
        typer.echo(f"[sma_slope_compute] index_code  = {index_code}")
        typer.echo(f"[sma_slope_compute] date range  = {start_date} → {end_date}")

        # Resolve tickers
        instruments = self.ingestor.get_index_instruments(index_code)
        tickers = [i.get("ticker", i.get("symbol", "")) for i in instruments]
        if ticker:
            tickers = [t for t in tickers if t == ticker.upper()]
        if limit:
            tickers = tickers[:limit]
        typer.echo(f"[sma_slope_compute] tickers     = {len(tickers)}")
        typer.echo(f"[sma_slope_compute] configs     = {slope_configs}")

        # Process each ticker (continue-on-failure)
        summary_rows: list[dict] = []

        for tkr in tickers:
            result = self._process_ticker(
                tkr, slope_configs, start_date, end_date, job_run_id,
            )
            summary_rows.append(result)

            # Audit item
            self.job_run_item_repo.create(
                job_run_id=job_run_id,
                item_key=tkr,
                status=result["status"],
                message=result.get("error"),
                details={
                    "slope_configs": slope_configs,
                    "sma_rows_read": result["sma_rows_read"],
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
        typer.echo(f"[sma_slope_compute] status = {final_status}")

    # ------------------------------------------------------------------
    # Per-ticker processing
    # ------------------------------------------------------------------

    def _process_ticker(
        self,
        tkr: str,
        slope_configs: list[dict],
        start_date: date,
        end_date: date,
        job_run_id: str,
    ) -> dict:
        """Read SMA values from DB, compute slope, upsert rows."""
        result: dict = {
            "ticker": tkr,
            "status": "SUCCESS",
            "sma_rows_read": 0,
            "rows_written": 0,
            "min_date": "",
            "max_date": "",
            "error": "",
        }
        try:
            rows_to_upsert: list[dict] = []

            for cfg in slope_configs:
                sma_window = cfg["sma_window"]
                slope_period = cfg["slope_period"]

                # Read existing SMA values from same-context DB (§1.1)
                sma_params = {"window": sma_window}
                sma_rows = self.indicator_repo.get_series(
                    ticker=tkr,
                    indicator_key="sma",
                    params_json=sma_params,
                    from_date=start_date,
                    to_date=end_date,
                )
                result["sma_rows_read"] = len(sma_rows)

                if len(sma_rows) < slope_period + 1:
                    result["error"] = (
                        f"insufficient SMA data: {len(sma_rows)} rows "
                        f"(need ≥{slope_period + 1} for slope_period={slope_period})"
                    )
                    continue

                # Build a pandas Series from DB rows
                sma_df = pd.DataFrame(sma_rows)
                sma_df = sma_df.sort_values("as_of_date").reset_index(drop=True)
                sma_series = sma_df["value"].astype(float)

                # Compute slope
                slope_series = compute_sma_slope(sma_series, slope_period)

                # Build upsert rows — params follow ADR-0001 naming
                params_json = json.dumps(
                    {"sma_window": sma_window, "slope_period": slope_period},
                    sort_keys=True,
                )

                for idx in range(slope_period, len(sma_df)):
                    val = slope_series.iloc[idx]
                    if pd.isna(val):
                        continue
                    rows_to_upsert.append(
                        {
                            "ticker": tkr,
                            "as_of_date": sma_df["as_of_date"].iloc[idx],
                            "indicator_key": "sma_slope",
                            "params_json": params_json,
                            "value": round(float(val), 8),
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
