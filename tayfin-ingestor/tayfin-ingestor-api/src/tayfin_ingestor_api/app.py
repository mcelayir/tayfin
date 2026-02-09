import os
from flask import Flask, request, jsonify
from .db.engine import get_engine
from .repositories.fundamentals_repository import FundamentalsRepository
from datetime import date

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

    return app


app = create_app()
