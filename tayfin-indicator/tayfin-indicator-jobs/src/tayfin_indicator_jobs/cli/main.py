"""Typer CLI entry-point for tayfin-indicator-jobs."""

import typer

app = typer.Typer()
jobs_app = typer.Typer()
app.add_typer(jobs_app, name="jobs")


@jobs_app.command("list")
def list_jobs() -> None:
    """List configured indicator jobs (placeholder)."""
    typer.echo("No indicator jobs configured yet.")
    raise typer.Exit(code=0)
