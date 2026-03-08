"""Flask application factory for tayfin-screener-api.

Read-only API over precomputed screening results (§6.1 ARCHITECTURE_RULES).

Endpoints
---------
* ``GET /health``               — DB connectivity check
* ``GET /vcp/latest``           — latest VCP results (all tickers)
* ``GET /vcp/latest/<ticker>``  — latest VCP result for one ticker
* ``GET /vcp/range``            — VCP results for a ticker over a date range
* ``GET /mcsa/latest``          — latest MCSA results (all tickers)
* ``GET /mcsa/latest/<ticker>`` — latest MCSA result for one ticker
* ``GET /mcsa/range``           — MCSA results for a ticker over a date range
"""

from __future__ import annotations

import json
import re
from datetime import date

from flask import Flask, jsonify, request

from .db import get_engine
from .repositories.mcsa_repository import (
    get_latest_all as mcsa_get_latest_all,
    get_latest_by_ticker as mcsa_get_latest_by_ticker,
    get_range_by_ticker as mcsa_get_range_by_ticker,
)
from .repositories.vcp_repository import (
    get_latest_all,
    get_latest_by_ticker,
    get_range_by_ticker,
    ping_db,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_RANGE_DAYS = 5 * 365
_MAX_LIMIT = 1000


def _parse_date(value: str) -> date:
    if not _DATE_RE.match(value):
        raise ValueError(f"invalid date format: {value}")
    return date.fromisoformat(value)


def _serialise_row(row: dict) -> dict:
    """Convert a DB row dict into a JSON-safe representation."""
    out: dict = {}
    out["ticker"] = row["ticker"]
    out["instrument_id"] = str(row["instrument_id"]) if row.get("instrument_id") else None
    aod = row["as_of_date"]
    out["as_of_date"] = aod.isoformat() if hasattr(aod, "isoformat") else str(aod)
    out["vcp_score"] = float(row["vcp_score"])
    out["vcp_confidence"] = row["vcp_confidence"]
    out["pattern_detected"] = bool(row["pattern_detected"])

    fj = row.get("features_json")
    if isinstance(fj, str):
        fj = json.loads(fj)
    out["features_json"] = fj
    return out


def _serialise_mcsa_row(row: dict) -> dict:
    """Convert an MCSA DB row dict into a JSON-safe representation."""
    out: dict = {}
    out["ticker"] = row["ticker"]
    out["instrument_id"] = str(row["instrument_id"]) if row.get("instrument_id") else None
    aod = row["as_of_date"]
    out["as_of_date"] = aod.isoformat() if hasattr(aod, "isoformat") else str(aod)
    out["mcsa_pass"] = bool(row["mcsa_pass"])
    out["rs_rank"] = float(row["rs_rank"]) if row.get("rs_rank") is not None else None
    out["criteria_count_pass"] = int(row["criteria_count_pass"])

    cj = row.get("criteria_json")
    if isinstance(cj, str):
        cj = json.loads(cj)
    out["criteria_json"] = cj
    return out


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @app.get("/health")
    def health():
        try:
            engine = get_engine()
            if not ping_db(engine):
                return jsonify({"status": "error", "detail": "db check failed"}), 500
        except Exception as exc:
            return jsonify({"status": "error", "detail": str(exc)}), 500
        return jsonify({"status": "ok"})

    # ------------------------------------------------------------------
    # GET /vcp/latest — all tickers, latest per ticker
    # ------------------------------------------------------------------

    @app.get("/vcp/latest")
    def vcp_latest_all():
        """Return the latest VCP result for every screened ticker.

        Query params
        ~~~~~~~~~~~~
        * ``pattern_only`` — ``true`` to return only detected patterns
        * ``min_score``    — minimum VCP score (0–100)
        * ``limit``        — max results (default 500, max 1000)
        * ``offset``       — pagination offset
        """
        pattern_only = request.args.get("pattern_only", "").lower() == "true"

        min_score: float | None = None
        raw_score = request.args.get("min_score")
        if raw_score is not None:
            try:
                min_score = float(raw_score)
            except ValueError:
                return jsonify({"error": "bad_param", "detail": "min_score must be numeric"}), 400

        try:
            limit = min(int(request.args.get("limit", 500)), _MAX_LIMIT)
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify({"error": "bad_param", "detail": "limit/offset must be integers"}), 400

        engine = get_engine()
        rows = get_latest_all(
            engine,
            pattern_only=pattern_only,
            min_score=min_score,
            limit=limit,
            offset=offset,
        )
        return jsonify({"items": [_serialise_row(r) for r in rows]})

    # ------------------------------------------------------------------
    # GET /vcp/latest/<ticker> — single ticker
    # ------------------------------------------------------------------

    @app.get("/vcp/latest/<ticker>")
    def vcp_latest_ticker(ticker: str):
        """Return the most recent VCP result for one ticker."""
        engine = get_engine()
        row = get_latest_by_ticker(engine, ticker.upper())
        if row is None:
            return jsonify({
                "error": "not_found",
                "detail": f"no VCP data for {ticker.upper()}",
            }), 404
        return jsonify(_serialise_row(row))

    # ------------------------------------------------------------------
    # GET /vcp/range — date range for a ticker
    # ------------------------------------------------------------------

    @app.get("/vcp/range")
    def vcp_range():
        """Return VCP results for a ticker over a date range.

        Query params
        ~~~~~~~~~~~~
        * ``ticker`` — required
        * ``from``   — YYYY-MM-DD, required
        * ``to``     — YYYY-MM-DD, required
        """
        ticker = request.args.get("ticker")
        from_str = request.args.get("from")
        to_str = request.args.get("to")

        if not ticker or not from_str or not to_str:
            return jsonify({
                "error": "missing_params",
                "detail": "ticker, from, and to are required",
            }), 400

        try:
            from_date = _parse_date(from_str)
            to_date = _parse_date(to_str)
        except ValueError as exc:
            return jsonify({"error": "bad_date", "detail": str(exc)}), 400

        if from_date > to_date:
            return jsonify({"error": "bad_range", "detail": "from must be <= to"}), 400
        if (to_date - from_date).days > _MAX_RANGE_DAYS:
            return jsonify({
                "error": "range_too_large",
                "detail": f"max range is {_MAX_RANGE_DAYS} days (~5 years)",
            }), 400

        engine = get_engine()
        rows = get_range_by_ticker(engine, ticker.upper(), from_date, to_date)
        return jsonify({
            "ticker": ticker.upper(),
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "items": [_serialise_row(r) for r in rows],
        })

    # ==================================================================
    # MCSA Endpoints
    # ==================================================================

    # ------------------------------------------------------------------
    # GET /mcsa/latest — all tickers, latest per ticker
    # ------------------------------------------------------------------

    @app.get("/mcsa/latest")
    def mcsa_latest_all():
        """Return the latest MCSA result for every screened ticker.

        Query params
        ~~~~~~~~~~~~
        * ``pass_only``     — ``true`` to return only passing tickers
        * ``min_criteria``  — minimum criteria count (0–8)
        * ``limit``         — max results (default 500, max 1000)
        * ``offset``        — pagination offset
        """
        pass_only = request.args.get("pass_only", "").lower() == "true"

        min_criteria: int | None = None
        raw_criteria = request.args.get("min_criteria")
        if raw_criteria is not None:
            try:
                min_criteria = int(raw_criteria)
            except ValueError:
                return jsonify({"error": "bad_param", "detail": "min_criteria must be integer"}), 400

        try:
            limit = min(int(request.args.get("limit", 500)), _MAX_LIMIT)
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify({"error": "bad_param", "detail": "limit/offset must be integers"}), 400

        engine = get_engine()
        rows = mcsa_get_latest_all(
            engine,
            pass_only=pass_only,
            min_criteria=min_criteria,
            limit=limit,
            offset=offset,
        )
        return jsonify({"items": [_serialise_mcsa_row(r) for r in rows]})

    # ------------------------------------------------------------------
    # GET /mcsa/latest/<ticker> — single ticker
    # ------------------------------------------------------------------

    @app.get("/mcsa/latest/<ticker>")
    def mcsa_latest_ticker(ticker: str):
        """Return the most recent MCSA result for one ticker."""
        engine = get_engine()
        row = mcsa_get_latest_by_ticker(engine, ticker.upper())
        if row is None:
            return jsonify({
                "error": "not_found",
                "detail": f"no MCSA data for {ticker.upper()}",
            }), 404
        return jsonify(_serialise_mcsa_row(row))

    # ------------------------------------------------------------------
    # GET /mcsa/range — date range for a ticker
    # ------------------------------------------------------------------

    @app.get("/mcsa/range")
    def mcsa_range():
        """Return MCSA results for a ticker over a date range.

        Query params
        ~~~~~~~~~~~~
        * ``ticker`` — required
        * ``from``   — YYYY-MM-DD, required
        * ``to``     — YYYY-MM-DD, required
        """
        ticker = request.args.get("ticker")
        from_str = request.args.get("from")
        to_str = request.args.get("to")

        if not ticker or not from_str or not to_str:
            return jsonify({
                "error": "missing_params",
                "detail": "ticker, from, and to are required",
            }), 400

        try:
            from_date = _parse_date(from_str)
            to_date = _parse_date(to_str)
        except ValueError as exc:
            return jsonify({"error": "bad_date", "detail": str(exc)}), 400

        if from_date > to_date:
            return jsonify({"error": "bad_range", "detail": "from must be <= to"}), 400
        if (to_date - from_date).days > _MAX_RANGE_DAYS:
            return jsonify({
                "error": "range_too_large",
                "detail": f"max range is {_MAX_RANGE_DAYS} days (~5 years)",
            }), 400

        engine = get_engine()
        rows = mcsa_get_range_by_ticker(engine, ticker.upper(), from_date, to_date)
        return jsonify({
            "ticker": ticker.upper(),
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "items": [_serialise_mcsa_row(r) for r in rows],
        })

    return app
