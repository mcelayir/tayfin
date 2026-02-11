import typer
from typing import Optional
from pathlib import Path

from ..config.loader import load_config
from ..jobs.discovery_job import DiscoveryJob
from ..jobs.fundamentals_job import FundamentalsJob
from ..jobs.ohlcv_job import OhlcvJob

app = typer.Typer()
jobs_app = typer.Typer()
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs(config: Optional[Path] = typer.Option(None, help="Path to config YAML"), kind: Optional[str] = typer.Option(None, help="Job kind to list (discovery|fundamentals|ohlcv)")):
    """List targets from config. Use --kind to select job type."""
    if kind == "fundamentals":
        cfg = load_config(config, default_filename="fundamentals.yml")
        targets = cfg.get("jobs", {}).get("fundamentals", {})
        if not targets:
            typer.echo("No fundamentals targets found in config.")
            raise typer.Exit(code=0)
        for name, entry in targets.items():
            typer.echo(f"- {name}: {entry.get('name', '')} ({entry.get('index_code','')})")
        raise typer.Exit(code=0)

    if kind == "ohlcv":
        cfg = load_config(config, default_filename="ohlcv.yml")
        targets = cfg.get("jobs", {}).get("ohlcv", {})
        if not targets:
            typer.echo("No ohlcv targets found in config.")
            raise typer.Exit(code=0)
        for name, entry in targets.items():
            typer.echo(f"- {name}: code={entry.get('code', '')} index_code={entry.get('index_code','')} timeframe={entry.get('timeframe','')} window_days={entry.get('window_days','')}")
        raise typer.Exit(code=0)

    # Default: discovery
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
    ticker: Optional[str] = typer.Option(None, help="Optional ticker override (single instrument)"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date override (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date override (YYYY-MM-DD)"),
):
    """Run a job. Example: jobs run discovery nasdaq-100 --config config/discovery.yml"""
    cfg = None
    target_cfg = None
    if kind == "discovery":
        cfg = load_config(config)
        targets = cfg.get("jobs", {}).get("discovery", {})
        target_cfg = targets.get(target)
        if not target_cfg:
            typer.echo(f"Discovery target '{target}' not found in config.")
            raise typer.Exit(code=1)
        job = DiscoveryJob.from_config(target_cfg, cfg)
        result = job.run()
    elif kind == "fundamentals":
        cfg = load_config(config, default_filename="fundamentals.yml")
        targets = cfg.get("jobs", {}).get("fundamentals", {})
        target_cfg = targets.get(target)
        if not target_cfg:
            typer.echo(f"Fundamentals target '{target}' not found in config.")
            raise typer.Exit(code=1)
        job = FundamentalsJob.from_config(target_cfg, cfg)
        # optional ticker override
        result = job.run(ticker=ticker)
    elif kind == "ohlcv":
        cfg = load_config(config, default_filename="ohlcv.yml")
        targets = cfg.get("jobs", {}).get("ohlcv", {})
        target_cfg = targets.get(target)
        if not target_cfg:
            typer.echo(f"OHLCV target '{target}' not found in config.")
            raise typer.Exit(code=1)
        job = OhlcvJob.from_config(target_cfg, cfg)
        job.run(ticker=ticker, from_date=from_date, to_date=to_date)
        return
    else:
        typer.echo("Unsupported job kind. Use 'discovery', 'fundamentals', or 'ohlcv'.")
        raise typer.Exit(code=1)
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
