"""Typer CLI entry-point for tayfin-indicator-jobs."""

from pathlib import Path
from typing import Optional

import typer

from ..config.loader import load_config
from ..jobs.registry import get_job_class

app = typer.Typer()
jobs_app = typer.Typer()
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs(
    config: Optional[Path] = typer.Option(None, help="Path to config YAML"),
    kind: Optional[str] = typer.Option(None, help="Job kind to list"),
) -> None:
    """List configured indicator jobs and their targets."""
    cfg = load_config(config)
    jobs_cfg = cfg.get("jobs", {})
    if not jobs_cfg:
        typer.echo("No indicator jobs found in config.")
        raise typer.Exit(code=0)

    for job_name, job_def in jobs_cfg.items():
        if kind and job_name != kind:
            continue
        targets = job_def.get("targets", {})
        typer.echo(f"job: {job_name}")
        for tgt_name, tgt_def in targets.items():
            indicators = tgt_def.get("indicators", [])
            ind_summary = ", ".join(
                f"{i['key']}({i.get('params', {})})" for i in indicators
            )
            typer.echo(
                f"  - {tgt_name}: index_code={tgt_def.get('index_code', '')} "
                f"indicators=[{ind_summary}]"
            )


@jobs_app.command("run")
def run_job(
    job_name: str = typer.Argument(..., help="Job name, e.g. ma_compute"),
    target: str = typer.Argument(..., help="Target name from config, e.g. nasdaq-100"),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML"),
    ticker: Optional[str] = typer.Option(None, help="Single ticker override"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit number of tickers"),
) -> None:
    """Run an indicator job. Example: jobs run ma_compute nasdaq-100 --config config/indicator.yml"""
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

    # Resolve job class from registry
    try:
        job_cls = get_job_class(job_name)
    except KeyError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    job = job_cls.from_config(target_name=target, target_cfg=target_cfg, full_cfg=cfg)
    job.run(ticker=ticker, limit=limit)
