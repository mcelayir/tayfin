"""MaComputeJob — stub job for moving-average indicator computation.

This job currently:
- creates a job_run record in tayfin_indicator.job_runs
- logs the configured indicators
- marks the run as SUCCESS

Actual indicator computation will be added in a later task.
"""

from __future__ import annotations

import typer

from ..db.engine import get_engine
from ..repositories.job_run_repository import JobRunRepository


class MaComputeJob:
    """Compute moving-average family indicators for a given target."""

    def __init__(self, target_name: str, target_cfg: dict, full_cfg: dict):
        self.target_name = target_name
        self.target_cfg = target_cfg
        self.full_cfg = full_cfg
        self.engine = get_engine()
        self.job_run_repo = JobRunRepository(self.engine)

    @classmethod
    def from_config(cls, target_name: str, target_cfg: dict, full_cfg: dict) -> "MaComputeJob":
        """Construct from parsed YAML config."""
        return cls(target_name=target_name, target_cfg=target_cfg, full_cfg=full_cfg)

    def run(
        self,
        ticker: str | None = None,
        limit: int | None = None,
    ) -> None:
        """Execute the stub job."""
        indicators = self.target_cfg.get("indicators", [])

        # Build params snapshot for auditing
        params = {
            "target_name": self.target_name,
            "index_code": self.target_cfg.get("index_code"),
            "country": self.target_cfg.get("country"),
            "indicators": indicators,
            "cli_overrides": {
                "ticker": ticker,
                "limit": limit,
            },
        }

        # Create job_run
        job_run_id = self.job_run_repo.create(
            job_name="ma_compute",
            target_name=self.target_name,
            status="RUNNING",
            params=params,
        )

        typer.echo(f"[ma_compute] job_run_id = {job_run_id}")
        typer.echo(f"[ma_compute] target     = {self.target_name}")
        typer.echo(f"[ma_compute] index_code = {self.target_cfg.get('index_code')}")
        typer.echo(f"[ma_compute] indicators:")
        for ind in indicators:
            typer.echo(f"  - {ind['key']}  params={ind.get('params', {})}")

        # Stub: no computation yet
        typer.echo("[ma_compute] (stub) no computation performed — completing run")

        # Finalize as SUCCESS
        self.job_run_repo.finalize(
            job_run_id=job_run_id,
            status="SUCCESS",
            message=f"stub run for {self.target_name}: {len(indicators)} indicator(s) configured",
        )

        typer.echo(f"[ma_compute] status = SUCCESS")
