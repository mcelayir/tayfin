"""Typer CLI for the tayfin-bff service.

Usage:
    python -m tayfin_bff serve          # defaults: 0.0.0.0:8030
    python -m tayfin_bff serve --port 9000
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="tayfin-bff",
    help="Backend-For-Frontend proxy for the Tayfin UI.",
    no_args_is_help=True,
)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address"),
    port: int = typer.Option(8030, help="Port (default 8030 per ARCH §6)"),
    debug: bool = typer.Option(False, help="Enable Flask debug mode"),
) -> None:
    """Start the BFF HTTP server."""
    from tayfin_bff.app import create_app

    flask_app = create_app()
    flask_app.run(host=host, port=port, debug=debug)
