import os
import re
from flask import Flask, request, jsonify
from .db.engine import get_engine
from .repositories.fundamentals_repository import FundamentalsRepository
from datetime import date

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value: str) -> date:
    """Parse a YYYY-MM-DD string into a date, raising ValueError on bad format or invalid date."""
    if not _DATE_RE.match(value):
        raise ValueError(f"invalid date format: {value}")
    return date.fromisoformat(value)


def create_app():
    app = Flask(__name__)

    # create engine/repo lazily inside handlers to avoid requiring DB driver at import time

    @app.get('/health')
    def health():
        return jsonify({"status": "ok"})

    @app.get('/fundamentals/latest')
    def latest():
        symbol = request.args.get('symbol')
        country = request.args.get('country', 'US')
        source = request.args.get('source', 'stockdex_yahoo')

        if not symbol:
            return jsonify({"error": "symbol_required", "details": "query param 'symbol' is required"}), 400

        engine = get_engine()
        repo = FundamentalsRepository(engine)
        instr = repo.resolve_instrument(symbol.upper(), country.upper())
        if not instr:
            return jsonify({"error": "instrument_not_found", "details": f"{symbol} {country}"}), 404

        row = repo.get_latest_snapshot(instr['id'], source)
        if not row:
            return jsonify({"error": "snapshot_not_found", "details": f"no snapshot for {symbol} {country} {source}"}), 404

        resp = {"symbol": symbol.upper(), "country": country.upper(), "source": source, "as_of_date": row['as_of_date'].isoformat()}
        resp.update(row['metrics'])
        return jsonify(resp)

    @app.get('/fundamentals')
    def range_query():
        symbol = request.args.get('symbol')
        country = request.args.get('country', 'US')
        source = request.args.get('source', 'stockdex_yahoo')
        fr = request.args.get('from')
        to = request.args.get('to')
        order = request.args.get('order', 'asc').lower()
        try:
            limit = int(request.args.get('limit', '365'))
        except ValueError:
            return jsonify({"error": "invalid_limit", "details": "limit must be integer"}), 400

        if not symbol:
            return jsonify({"error": "symbol_required", "details": "query param 'symbol' is required"}), 400
        if limit < 1 or limit > 2000:
            return jsonify({"error": "invalid_limit", "details": "limit must be between 1 and 2000"}), 400
        if order not in ('asc', 'desc'):
            return jsonify({"error": "invalid_order", "details": "order must be 'asc' or 'desc'"}), 400

        fr_date = None
        to_date = None
        try:
            if fr:
                fr_date = date.fromisoformat(fr)
            if to:
                to_date = date.fromisoformat(to)
        except Exception:
            return jsonify({"error": "invalid_date", "details": "dates must be YYYY-MM-DD"}), 400

        engine = get_engine()
        repo = FundamentalsRepository(engine)
        instr = repo.resolve_instrument(symbol.upper(), country.upper())
        if not instr:
            return jsonify({"error": "instrument_not_found", "details": f"{symbol} {country}"}), 404

        items = repo.get_snapshots_range(instr['id'], source, fr_date, to_date, limit, order)

        resp = {
            "symbol": symbol.upper(),
            "country": country.upper(),
            "source": source,
            "from": fr_date.isoformat() if fr_date else None,
            "to": to_date.isoformat() if to_date else None,
            "count": len(items),
            "items": items,
        }
        return jsonify(resp)

    @app.get('/indices/members')
    def index_members():
        index_code = request.args.get('index_code')
        country = request.args.get('country', 'US')
        order = request.args.get('order', 'asc').lower()
        try:
            limit = int(request.args.get('limit', '200'))
        except ValueError:
            return jsonify({"error": "invalid_limit", "details": "limit must be integer"}), 400

        if not index_code:
            return jsonify({"error": "index_code_required", "details": "query param 'index_code' is required"}), 400
        if limit < 1 or limit > 5000:
            return jsonify({"error": "invalid_limit", "details": "limit must be between 1 and 5000"}), 400
        if order not in ('asc', 'desc'):
            return jsonify({"error": "invalid_order", "details": "order must be 'asc' or 'desc'"}), 400

        engine = get_engine()
        from .repositories.index_membership_repository import IndexMembershipRepository
        repo = IndexMembershipRepository(engine)

        items = repo.get_members(index_code.upper(), country.upper(), limit, order)
        if not items:
            return jsonify({"error": "not_found", "details": f"no members for index {index_code}"}), 404

        return jsonify({"index_code": index_code.upper(), "country": country.upper(), "count": len(items), "items": items})

    @app.get('/indices/by-symbol')
    def indices_by_symbol():
        symbol = request.args.get('symbol')
        country = request.args.get('country', 'US')
        try:
            limit = int(request.args.get('limit', '1000'))
        except ValueError:
            return jsonify({"error": "invalid_limit", "details": "limit must be integer"}), 400

        if not symbol:
            return jsonify({"error": "symbol_required", "details": "query param 'symbol' is required"}), 400

        engine = get_engine()
        from .repositories.instrument_repository import InstrumentRepository
        from .repositories.index_membership_repository import IndexMembershipRepository
        instr_repo = InstrumentRepository(engine)
        repo = IndexMembershipRepository(engine)

        instr = instr_repo.resolve(symbol.upper(), country.upper())
        if not instr:
            return jsonify({"error": "instrument_not_found", "details": f"{symbol} {country}"}), 404

        items = repo.get_indices_for_instrument(instr['id'], limit)
        return jsonify({"symbol": symbol.upper(), "country": country.upper(), "count": len(items), "items": items})

    @app.get('/markets/instruments')
    def market_instruments():
        market = request.args.get('market')
        if not market:
            return jsonify({"error": "market_required", "details": "query param 'market' is required"}), 400
        return jsonify({"error": "not_implemented", "details": "Market universe is not stored yet. Implement exchange listings ingestion first."}), 501

    # ------------------------------------------------------------------
    # OHLCV endpoint
    # ------------------------------------------------------------------

    @app.get('/ohlcv')
    def ohlcv():
        """Unified OHLCV endpoint.

        Without from/to → returns the latest candle(s) for the given selector.
        With from/to    → returns a date-range series (ticker only).
        """
        ticker = request.args.get('ticker')
        index_code = request.args.get('index_code')
        market_code = request.args.get('market_code')
        from_str = request.args.get('from')
        to_str = request.args.get('to')
        has_dates = bool(from_str or to_str)

        if has_dates:
            # ---------- Range mode: ticker only ----------
            if index_code or market_code:
                return jsonify({"error": "invalid_request", "message": "'index_code' and 'market_code' are not allowed with date parameters — omit from/to for latest"}), 400

            if not ticker:
                return jsonify({"error": "invalid_request", "message": "'ticker' is required"}), 400
            ticker = ticker.strip().upper()
            if not ticker:
                return jsonify({"error": "invalid_request", "message": "'ticker' must not be blank"}), 400

            from_date = None
            to_date = None
            try:
                if from_str:
                    from_date = _parse_date(from_str)
                if to_str:
                    to_date = _parse_date(to_str)
            except ValueError:
                return jsonify({"error": "invalid_request", "message": "Dates must be valid YYYY-MM-DD"}), 400

            if from_date and to_date and from_date > to_date:
                return jsonify({"error": "invalid_request", "message": "'from' must not be after 'to'"}), 400

            engine = get_engine()
            from .repositories.ohlcv_repository import OhlcvRepository
            from .serializers.ohlcv_serializer import serialize_series
            ohlcv_repo = OhlcvRepository(engine)

            items = ohlcv_repo.get_range_by_ticker(ticker, from_date, to_date)
            if items is None:
                return jsonify({"error": "not_found", "message": f"Instrument '{ticker}' not found"}), 404

            return jsonify(serialize_series(ticker, from_date, to_date, items))

        # ---------- Latest mode: exactly one selector ----------
        provided = [p for p in (ticker, index_code, market_code) if p]
        if len(provided) == 0:
            return jsonify({"error": "invalid_request", "message": "Exactly one of 'ticker', 'index_code', or 'market_code' is required"}), 400
        if len(provided) > 1:
            return jsonify({"error": "invalid_request", "message": "Provide only one of 'ticker', 'index_code', or 'market_code'"}), 400

        # Normalize
        if ticker:
            ticker = ticker.strip().upper()
            if not ticker:
                return jsonify({"error": "invalid_request", "message": "'ticker' must not be blank"}), 400
        if index_code:
            index_code = index_code.strip().upper()
            if not index_code:
                return jsonify({"error": "invalid_request", "message": "'index_code' must not be blank"}), 400
        if market_code:
            market_code = market_code.strip().upper()
            if not market_code:
                return jsonify({"error": "invalid_request", "message": "'market_code' must not be blank"}), 400

        # Dispatch by selector
        engine = get_engine()
        from .repositories.ohlcv_repository import OhlcvRepository
        from .serializers.ohlcv_serializer import serialize_candle, serialize_index_latest
        ohlcv_repo = OhlcvRepository(engine)

        if ticker:
            row = ohlcv_repo.get_latest_by_ticker(ticker)
            if not row:
                return jsonify({"error": "not_found", "message": f"No OHLCV data found for ticker '{ticker}'"}), 404
            return jsonify(serialize_candle(row))

        if index_code:
            items = ohlcv_repo.get_latest_by_index(index_code)
            if not items:
                return jsonify({"error": "not_found", "message": f"No OHLCV data found for index '{index_code}'"}), 404
            return jsonify(serialize_index_latest(index_code, items))

        # market_code — no market membership table yet
        return jsonify({"error": "not_implemented", "message": "market_code lookup is not implemented yet"}), 501

    return app


app = create_app()
