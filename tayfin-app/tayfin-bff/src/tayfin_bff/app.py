"""Flask application factory for the Tayfin BFF.

Server-rendered HTMX + Jinja2 dashboard (ADR-0001 §D3).

The BFF is the sole gateway between the UI and the context APIs
(§2.2 — UI calls only BFF; BFF calls context APIs).

Endpoints
---------
Pages (HTML):
* ``GET /``                     — redirect to MCSA dashboard
* ``GET /mcsa``                 — MCSA Trend Template dashboard

API proxy (JSON — consumed by HTMX):
* ``GET /api/mcsa/latest``      — latest MCSA results (all tickers)
* ``GET /api/mcsa/latest/<t>``  — latest MCSA result for one ticker
* ``GET /api/mcsa/range``       — MCSA history for a ticker
* ``GET /api/mcsa/rs-histogram``— RS rank distribution for histogram

HTMX partials (HTML fragments):
* ``GET /htmx/mcsa/table``      — results table partial
* ``GET /htmx/mcsa/histogram``  — RS histogram partial

Health:
* ``GET /health``               — BFF + downstream health
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from .clients.screener_client import ScreenerClient

logger = logging.getLogger(__name__)

_MAX_LIMIT = 1000


def create_app() -> Flask:
    """Application factory."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # Lazily initialised client (allows env vars to be set before first request)
    _client: ScreenerClient | None = None

    def _screener() -> ScreenerClient:
        nonlocal _client
        if _client is None:
            _client = ScreenerClient()
        return _client

    # ==================================================================
    # Health
    # ==================================================================

    @app.get("/health")
    def health():
        screener_ok = _screener().health()
        status = "ok" if screener_ok else "degraded"
        return jsonify({
            "status": status,
            "downstream": {"screener": "ok" if screener_ok else "error"},
        }), 200 if screener_ok else 503

    # ==================================================================
    # Pages (server-rendered HTML)
    # ==================================================================

    @app.get("/")
    def index():
        return redirect(url_for("mcsa_dashboard"))

    @app.get("/mcsa")
    def mcsa_dashboard():
        """Render the full MCSA dashboard page.

        The page skeleton loads immediately; data is fetched via HTMX
        partial requests for a snappy perceived load time.
        """
        return render_template("mcsa/dashboard.html")

    # ==================================================================
    # HTMX partials (HTML fragments)
    # ==================================================================

    @app.get("/htmx/mcsa/table")
    def htmx_mcsa_table():
        """Return an HTML table fragment of MCSA results.

        Query params (forwarded from HTMX):
        * ``pass_only``    — ``true`` to show only passing tickers
        * ``min_criteria`` — minimum criteria count (0–8)
        * ``sort``         — column to sort by (default: ``rs_rank``)
        * ``order``        — ``asc`` or ``desc`` (default: ``desc``)
        * ``limit``        — max results (default 100)
        """
        pass_only = request.args.get("pass_only", "").lower() == "true"

        min_criteria: int | None = None
        raw = request.args.get("min_criteria")
        if raw is not None:
            try:
                min_criteria = int(raw)
            except ValueError:
                min_criteria = None

        try:
            limit = min(int(request.args.get("limit", 100)), _MAX_LIMIT)
        except ValueError:
            limit = 100

        sort_col = request.args.get("sort", "rs_rank")
        sort_order = request.args.get("order", "desc")

        rows = _screener().get_mcsa_latest(
            pass_only=pass_only,
            min_criteria=min_criteria,
            limit=limit,
        )

        # Client-side sort (the screener API returns sorted by rs_rank desc,
        # but user may want to sort by other columns via HTMX)
        _sort_rows(rows, sort_col, sort_order)

        return render_template(
            "mcsa/_results_table.html",
            rows=rows,
            sort=sort_col,
            order=sort_order,
            pass_only=pass_only,
            min_criteria=min_criteria,
        )

    @app.get("/htmx/mcsa/histogram")
    def htmx_mcsa_histogram():
        """Return an HTML fragment containing the RS rank histogram.

        Buckets RS rank values into 10 bins (0–10, 10–20, ... 90–100)
        and returns a simple bar chart rendered as styled divs.
        """
        rows = _screener().get_mcsa_latest(limit=_MAX_LIMIT)
        histogram = _build_rs_histogram(rows)
        return render_template(
            "mcsa/_rs_histogram.html",
            histogram=histogram,
            total=len(rows),
        )

    # ==================================================================
    # JSON API proxy (for programmatic / HTMX JSON access)
    # ==================================================================

    @app.get("/api/mcsa/latest")
    def api_mcsa_latest():
        pass_only = request.args.get("pass_only", "").lower() == "true"
        min_criteria: int | None = None
        raw = request.args.get("min_criteria")
        if raw is not None:
            try:
                min_criteria = int(raw)
            except ValueError:
                return jsonify({"error": "bad_param", "detail": "min_criteria must be integer"}), 400
            if not (0 <= min_criteria <= 8):
                return jsonify({"error": "bad_param", "detail": "min_criteria must be between 0 and 8"}), 400

        try:
            raw_limit = int(request.args.get("limit", 500))
            limit = max(0, min(raw_limit, _MAX_LIMIT))
            raw_offset = int(request.args.get("offset", 0))
            offset = max(0, raw_offset)
        except ValueError:
            return jsonify({"error": "bad_param", "detail": "limit/offset must be integers"}), 400

        rows = _screener().get_mcsa_latest(
            pass_only=pass_only,
            min_criteria=min_criteria,
            limit=limit,
            offset=offset,
        )
        return jsonify({"items": rows})

    @app.get("/api/mcsa/latest/<ticker>")
    def api_mcsa_latest_ticker(ticker: str):
        row = _screener().get_mcsa_latest_ticker(ticker)
        if row is None:
            return jsonify({"error": "not_found", "detail": f"no MCSA data for {ticker.upper()}"}), 404
        return jsonify(row)

    @app.get("/api/mcsa/range")
    def api_mcsa_range():
        ticker = request.args.get("ticker")
        from_str = request.args.get("from")
        to_str = request.args.get("to")

        if not ticker or not from_str or not to_str:
            return jsonify({"error": "missing_params", "detail": "ticker, from, and to are required"}), 400

        rows = _screener().get_mcsa_range(ticker, from_str, to_str)
        return jsonify({
            "ticker": ticker.upper(),
            "from": from_str,
            "to": to_str,
            "items": rows,
        })

    @app.get("/api/mcsa/rs-histogram")
    def api_mcsa_rs_histogram():
        """Return RS rank distribution as JSON (Task 9b)."""
        rows = _screener().get_mcsa_latest(limit=_MAX_LIMIT)
        histogram = _build_rs_histogram(rows)
        return jsonify({
            "total": len(rows),
            "buckets": histogram,
        })

    return app


# ======================================================================
# Helpers
# ======================================================================

def _build_rs_histogram(rows: list[dict]) -> list[dict]:
    """Bucket RS rank values into 10 equal-width bins.

    Returns a list of ``{"range": "0-10", "count": N, "pct": float}`` dicts.
    """
    buckets = [0] * 10
    for row in rows:
        rs = row.get("rs_rank")
        if rs is None:
            continue
        idx = min(int(float(rs) // 10), 9)
        buckets[idx] += 1

    total = len(rows) or 1
    return [
        {
            "range": f"{i * 10}–{(i + 1) * 10}",
            "count": buckets[i],
            "pct": round(buckets[i] / total * 100, 1),
        }
        for i in range(10)
    ]


def _sort_rows(rows: list[dict], column: str, order: str) -> None:
    """Sort rows in-place by *column*.

    Handles missing values by pushing them to the end regardless of
    sort direction.
    """
    reverse = order.lower() != "asc"

    # Separate rows with values from rows with None
    with_val = [r for r in rows if r.get(column) is not None]
    without_val = [r for r in rows if r.get(column) is None]

    def _key(row: dict):
        val = row.get(column)
        try:
            return float(val)
        except (TypeError, ValueError):
            return str(val)

    with_val.sort(key=_key, reverse=reverse)

    rows.clear()
    rows.extend(with_val)
    rows.extend(without_val)
