"""Typer CLI entry-point for tayfin-screener-jobs."""

from pathlib import Path
from typing import Optional

import typer

from ..config.loader import load_config

app = typer.Typer()
jobs_app = typer.Typer()
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs(
    config: Optional[Path] = typer.Option(None, help="Path to config YAML"),
) -> None:
    """List configured screener jobs and their targets."""
    cfg = load_config(config)
    jobs_cfg = cfg.get("jobs", {})
    if not jobs_cfg:
        typer.echo("No screener jobs found in config.")
        raise typer.Exit(code=0)

    for job_name, job_def in jobs_cfg.items():
        targets = job_def.get("targets", {})
        typer.echo(f"job: {job_name}")
        for tgt_name, tgt_def in targets.items():
            typer.echo(
                f"  - {tgt_name}: index_code={tgt_def.get('index_code', '')}"
            )


@jobs_app.command("run")
def run_job(
    job_name: str = typer.Argument(..., help="Job name, e.g. vcp_screen"),
    target: str = typer.Argument(..., help="Target name from config, e.g. nasdaq-100"),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML"),
    ticker: Optional[str] = typer.Option(None, help="Single ticker override"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit number of tickers"),
) -> None:
    """Run a screener job. Example: jobs run vcp_screen nasdaq-100 --config config/screener.yml"""
    cfg = load_config(config)
    job_def = cfg.get("jobs", {}).get(job_name)
    if not job_def:
        typer.echo(f"Job '{job_name}' not found in config.")
        raise typer.Exit(code=1)

    targets = job_def.get("targets", {})
    target_cfg = targets.get(target)
    if not target_cfg:
        typer.echo(f"Target '{target}' not found under job '{job_name}'.")
        raise typer.Exit(code=1)

    # TODO: Wire job registry and dispatch here once jobs are implemented.
    typer.echo(f"Job '{job_name}' target '{target}' — not yet implemented.")
    raise typer.Exit(code=1)
