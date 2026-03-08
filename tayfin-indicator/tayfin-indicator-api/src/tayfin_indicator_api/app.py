"""Flask application factory for tayfin-indicator-api."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from flask import Flask, jsonify, request

from .clients.ingestor_client import IngestorClient
from .db.engine import get_engine
from .repositories.indicator_repository import (
    get_index_latest,
    get_latest,
    get_range,
    ping_db,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MAX_RANGE_DAYS = 5 * 365  # ~5 years


def _parse_date(value: str) -> date:
    if not _DATE_RE.match(value):
        raise ValueError(f"invalid date format: {value}")
    return date.fromisoformat(value)


def _build_params(window: str | None) -> dict | None:
    """Build params_json dict from optional window query param.
    
    Raises:
        ValueError: If window is provided but not a valid integer.
    """
    if window is None:
        return None
    try:
        return {"window": int(window)}
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid window parameter: {window}") from exc


# Reserved query params that are NOT part of params_json.
_RESERVED_PARAMS = frozenset({"index_code", "ticker", "from", "to"})


def _coerce_value(raw: str) -> int | float | str:
    """Best-effort coerce a query-string value to int or float."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _extract_params(args, reserved: frozenset = _RESERVED_PARAMS) -> dict | None:
    """Build a params_json dict from all query args not in *reserved*.

    Returns ``None`` when no indicator params are present.
    """
    params = {
        k: _coerce_value(v)
        for k, v in args.items()
        if k not in reserved
    }
    return params or None


def create_app():
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
    # GET /indicators/latest
    # ------------------------------------------------------------------

    @app.get("/indicators/latest")
    def indicators_latest():
        ticker = request.args.get("ticker")
        indicator = request.args.get("indicator")
        if not ticker or not indicator:
            return jsonify({"error": "missing_params", "detail": "ticker and indicator are required"}), 400

        try:
            params = _build_params(request.args.get("window"))
        except ValueError as exc:
            return jsonify({"error": "invalid_window", "detail": str(exc)}), 400

        engine = get_engine()
        row = get_latest(engine, ticker.upper(), indicator, params)
        if row is None:
            return jsonify({"error": "not_found", "detail": f"no data for {ticker} {indicator}"}), 404

        pj = row["params_json"]
        if isinstance(pj, str):
            pj = json.loads(pj)

        return jsonify({
            "ticker": row["ticker"],
            "as_of_date": row["as_of_date"].isoformat() if hasattr(row["as_of_date"], "isoformat") else str(row["as_of_date"]),
            "indicator": row["indicator_key"],
            "params": pj,
            "value": float(row["value"]),
            "source": row["source"],
        })

    # ------------------------------------------------------------------
    # GET /indicators/range
    # ------------------------------------------------------------------

    @app.get("/indicators/range")
    def indicators_range():
        ticker = request.args.get("ticker")
        indicator = request.args.get("indicator")
        from_str = request.args.get("from")
        to_str = request.args.get("to")

        if not ticker or not indicator or not from_str or not to_str:
            return jsonify({"error": "missing_params", "detail": "ticker, indicator, from, to are required"}), 400

        try:
            from_date = _parse_date(from_str)
            to_date = _parse_date(to_str)
        except ValueError as exc:
            return jsonify({"error": "bad_date", "detail": str(exc)}), 400

        if from_date > to_date:
            return jsonify({"error": "bad_range", "detail": "from must be <= to"}), 400

        if (to_date - from_date).days > _MAX_RANGE_DAYS:
            return jsonify({"error": "range_too_large", "detail": f"max range is {_MAX_RANGE_DAYS} days (~5 years)"}), 400

        try:
            params = _build_params(request.args.get("window"))
        except ValueError as exc:
            return jsonify({"error": "invalid_window", "detail": str(exc)}), 400

        engine = get_engine()
        rows = get_range(engine, ticker.upper(), indicator, from_date, to_date, params)

        items = [
            {
                "as_of_date": r["as_of_date"].isoformat() if hasattr(r["as_of_date"], "isoformat") else str(r["as_of_date"]),
                "value": float(r["value"]),
            }
            for r in rows
        ]

        resp: dict = {
            "ticker": ticker.upper(),
            "indicator": indicator,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "items": items,
        }
        if params:
            resp["params"] = params
        return jsonify(resp)

    # ------------------------------------------------------------------
    # GET /indicators/index/latest
    # ------------------------------------------------------------------

    @app.get("/indicators/index/latest")
    def indicators_index_latest():
        index_code = request.args.get("index_code")
        indicator = request.args.get("indicator")

        if not index_code or not indicator:
            return jsonify({"error": "missing_params", "detail": "index_code and indicator are required"}), 400

        try:
            params = _build_params(request.args.get("window"))
        except ValueError as exc:
            return jsonify({"error": "invalid_window", "detail": str(exc)}), 400

        engine = get_engine()
        
        # Fetch index members from the ingestor API
        ingestor = IngestorClient()
        tickers = ingestor.get_index_members(index_code)
        
        # Query indicators filtered by index membership
        rows = get_index_latest(engine, indicator, params, tickers=tickers)

        items = [
            {
                "ticker": r["ticker"],
                "as_of_date": r["as_of_date"].isoformat() if hasattr(r["as_of_date"], "isoformat") else str(r["as_of_date"]),
                "value": float(r["value"]),
            }
            for r in rows
        ]

        resp: dict = {
            "index_code": index_code.upper(),
            "indicator": indicator,
            "items": items,
        }
        if params:
            resp["params"] = params
        return jsonify(resp)

    # ------------------------------------------------------------------
    # GET /indicators/index/latest/<indicator>  (indicator-specific)
    # ------------------------------------------------------------------

    @app.get("/indicators/index/latest/<indicator>")
    def indicators_index_latest_by_name(indicator: str):
        """Indicator-specific endpoint — compound params as query args.

        Example::

            GET /indicators/index/latest/sma_slope?index_code=NDX&sma_window=200&slope_period=20
        """
        index_code = request.args.get("index_code")
        if not index_code:
            return jsonify({"error": "missing_params", "detail": "index_code is required"}), 400

        params = _extract_params(request.args)

        engine = get_engine()

        ingestor = IngestorClient()
        tickers = ingestor.get_index_members(index_code)

        rows = get_index_latest(engine, indicator, params, tickers=tickers)

        items = [
            {
                "ticker": r["ticker"],
                "as_of_date": r["as_of_date"].isoformat() if hasattr(r["as_of_date"], "isoformat") else str(r["as_of_date"]),
                "value": float(r["value"]),
            }
            for r in rows
        ]

        resp: dict = {
            "index_code": index_code.upper(),
            "indicator": indicator,
            "items": items,
        }
        if params:
            resp["params"] = params
        return jsonify(resp)

    # ------------------------------------------------------------------
    # GET /indicators/latest/<indicator>  (indicator-specific)
    # ------------------------------------------------------------------

    @app.get("/indicators/latest/<indicator>")
    def indicators_latest_by_name(indicator: str):
        """Indicator-specific endpoint — compound params as query args.

        Example::

            GET /indicators/latest/sma_slope?ticker=AAPL&sma_window=200&slope_period=20
        """
        ticker = request.args.get("ticker")
        if not ticker:
            return jsonify({"error": "missing_params", "detail": "ticker is required"}), 400

        params = _extract_params(request.args)

        engine = get_engine()
        row = get_latest(engine, ticker.upper(), indicator, params)
        if row is None:
            return jsonify({"error": "not_found", "detail": f"no data for {ticker} {indicator}"}), 404

        pj = row["params_json"]
        if isinstance(pj, str):
            pj = json.loads(pj)

        return jsonify({
            "ticker": row["ticker"],
            "as_of_date": row["as_of_date"].isoformat() if hasattr(row["as_of_date"], "isoformat") else str(row["as_of_date"]),
            "indicator": row["indicator_key"],
            "params": pj,
            "value": float(row["value"]),
            "source": row["source"],
        })

    # ------------------------------------------------------------------
    # GET /indicators/range/<indicator>  (indicator-specific)
    # ------------------------------------------------------------------

    @app.get("/indicators/range/<indicator>")
    def indicators_range_by_name(indicator: str):
        """Indicator-specific endpoint — compound params as query args.

        Example::

            GET /indicators/range/sma_slope?ticker=AAPL&from=2025-01-01&to=2026-01-01&sma_window=200&slope_period=20
        """
        ticker = request.args.get("ticker")
        from_str = request.args.get("from")
        to_str = request.args.get("to")

        if not ticker or not from_str or not to_str:
            return jsonify({"error": "missing_params", "detail": "ticker, from, to are required"}), 400

        try:
            from_date = _parse_date(from_str)
            to_date = _parse_date(to_str)
        except ValueError as exc:
            return jsonify({"error": "bad_date", "detail": str(exc)}), 400

        if from_date > to_date:
            return jsonify({"error": "bad_range", "detail": "from must be <= to"}), 400

        if (to_date - from_date).days > _MAX_RANGE_DAYS:
            return jsonify({"error": "range_too_large", "detail": f"max range is {_MAX_RANGE_DAYS} days (~5 years)"}), 400

        params = _extract_params(request.args)

        engine = get_engine()
        rows = get_range(engine, ticker.upper(), indicator, from_date, to_date, params)

        items = [
            {
                "as_of_date": r["as_of_date"].isoformat() if hasattr(r["as_of_date"], "isoformat") else str(r["as_of_date"]),
                "value": float(r["value"]),
            }
            for r in rows
        ]

        resp: dict = {
            "ticker": ticker.upper(),
            "indicator": indicator,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "items": items,
        }
        if params:
            resp["params"] = params
        return jsonify(resp)

    return app
