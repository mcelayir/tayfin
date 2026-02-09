import typer
from typing import Optional
from pathlib import Path

from ..config.loader import load_config
from ..jobs.discovery_job import DiscoveryJob

app = typer.Typer()
jobs_app = typer.Typer()
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs(config: Optional[Path] = typer.Option(None, help="Path to config YAML")):
    """List discovery targets from config."""
    cfg = load_config(config)
    targets = cfg.get("jobs", {}).get("discovery", {})
    if not targets:
        typer.echo("No discovery targets found in config.")
        raise typer.Exit(code=0)
    for name, entry in targets.items():
        typer.echo(f"- {name}: {entry.get('name', '')} ({entry.get('index_code','')})")


@jobs_app.command("run")
def run(
    kind: str = typer.Argument(..., help="Job kind, e.g. discovery"),
    target: str = typer.Argument(..., help="Target name from config"),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML"),
):
    """Run a job. Example: jobs run discovery nasdaq-100 --config config/discovery.yml"""
    if kind != "discovery":
        typer.echo("Only 'discovery' kind is supported in this skeleton.")
        raise typer.Exit(code=1)

    cfg = load_config(config)
    targets = cfg.get("jobs", {}).get("discovery", {})
    target_cfg = targets.get(target)
    if not target_cfg:
        typer.echo(f"Target '{target}' not found in config.")
        raise typer.Exit(code=1)

    job = DiscoveryJob.from_config(target_cfg, cfg)
    result = job.run()
    # result is a list of dicts with ticker,country,index_code
    import pandas as pd

    df = pd.DataFrame(result)
    if df.empty:
        typer.echo("No items discovered.")
    else:
        typer.echo(df.to_markdown(index=False))
    # Print counts
    total = len(result)
    succeeded = sum(1 for r in result if r.get("_status") == "SUCCESS")
    failed = total - succeeded
    typer.echo(f"Total: {total}, Succeeded: {succeeded}, Failed: {failed}")
