"""Flask application factory for tayfin-bff.

The BFF is a pure HTTP aggregator.  It has NO database.
It proxies requests to upstream context APIs (screener, indicator, ingestor)
and returns JSON for the Tayfin UI.

Architecture rules:
  - UI MUST call only the BFF   (ARCHITECTURE_RULES §2.2)
  - BFF MAY call any context API (§2.2)
  - BFF MUST NOT query any context database directly (§2.1)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .clients.screener_client import ScreenerClient

logger = logging.getLogger(__name__)

# Resolve tayfin-ui dist folder relative to this package.
# In production: tayfin-app/tayfin-ui/dist  (or override via TAYFIN_UI_DIST_DIR)
_DEFAULT_DIST = (
    Path(__file__).resolve().parents[4] / "tayfin-ui" / "dist"
)
_DIST_DIR = Path(os.environ.get("TAYFIN_UI_DIST_DIR", str(_DEFAULT_DIST)))


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    def health():
        """Liveness check — no DB, just confirm the process is running."""
        return jsonify({"status": "ok"})

    # ------------------------------------------------------------------
    # Static UI serving (production)
    # ------------------------------------------------------------------

    if _DIST_DIR.is_dir():
        @app.get("/")
        def serve_index():
            """Serve the UI index.html for the root route."""
            return send_from_directory(str(_DIST_DIR), "index.html")

        @app.get("/assets/<path:filename>")
        def serve_assets(filename: str):
            """Serve Vite build assets (JS, CSS, images)."""
            return send_from_directory(str(_DIST_DIR / "assets"), filename)

        @app.errorhandler(404)
        def fallback_to_spa(e):  # noqa: ARG001
            """SPA fallback — serve index.html for client-side routing."""
            return send_from_directory(str(_DIST_DIR), "index.html")

    # ------------------------------------------------------------------
    # MCSA Dashboard  (proxy to Screener API)
    # ------------------------------------------------------------------

    @app.get("/api/mcsa/dashboard")
    def mcsa_dashboard():
        """Return latest MCSA scores for all tickers.

        Query params forwarded to Screener API:
          band       — strong | watchlist | neutral | weak
          min_score  — minimum MCSA score (0–100)
          limit      — max rows (default 500, cap 1000)
          offset     — pagination offset
        """
        client = _screener_client()
        params: dict = {}
        if request.args.get("band"):
            params["band"] = request.args["band"]
        if request.args.get("min_score"):
            params["min_score"] = request.args["min_score"]
        if request.args.get("limit"):
            params["limit"] = request.args["limit"]
        if request.args.get("offset"):
            params["offset"] = request.args["offset"]

        data = client.get_mcsa_latest_all(params=params)
        if data is None:
            return jsonify({"error": "upstream_error", "detail": "Screener API unreachable"}), 502
        return jsonify(data)

    @app.get("/api/mcsa/<ticker>")
    def mcsa_ticker(ticker: str):
        """Return latest MCSA result for a single ticker."""
        client = _screener_client()
        data = client.get_mcsa_latest_ticker(ticker.upper())
        if data is None:
            return jsonify({"error": "not_found", "detail": f"no MCSA data for {ticker.upper()}"}), 404
        return jsonify(data)

    @app.get("/api/mcsa/range")
    def mcsa_range():
        """Return MCSA results for a ticker over a date range.

        Required query params: ticker, from, to
        """
        ticker = request.args.get("ticker")
        from_date = request.args.get("from")
        to_date = request.args.get("to")

        if not ticker or not from_date or not to_date:
            return jsonify({
                "error": "missing_params",
                "detail": "ticker, from, and to are required",
            }), 400

        client = _screener_client()
        data = client.get_mcsa_range(
            ticker=ticker.upper(),
            from_date=from_date,
            to_date=to_date,
        )
        if data is None:
            return jsonify({"error": "upstream_error", "detail": "Screener API unreachable"}), 502
        return jsonify(data)

    return app


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_client_instance: ScreenerClient | None = None


def _screener_client() -> ScreenerClient:
    """Lazy-init singleton ScreenerClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ScreenerClient()
    return _client_instance
