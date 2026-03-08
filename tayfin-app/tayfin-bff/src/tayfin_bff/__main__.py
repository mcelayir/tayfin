"""Typer CLI entry point for tayfin-bff (TECH_STACK_RULES §3)."""

from __future__ import annotations

import typer

app = typer.Typer(help="Tayfin BFF — HTMX dashboard server")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address"),
    port: int = typer.Option(8030, help="Bind port"),
    debug: bool = typer.Option(False, help="Enable Flask debug mode"),
) -> None:
    """Start the BFF development server."""
    from .app import create_app

    flask_app = create_app()
    flask_app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    app()
