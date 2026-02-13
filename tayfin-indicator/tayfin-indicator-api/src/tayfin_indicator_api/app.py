"""Flask application factory for tayfin-indicator-api."""

from flask import Flask, jsonify

from .db.engine import get_engine
from .repositories.indicator_repository import ping_db


def create_app():
    app = Flask(__name__)

    @app.get("/health")
    def health():
        try:
            engine = get_engine()
            if not ping_db(engine):
                return jsonify({"status": "error", "detail": "db check failed"}), 500
        except Exception as exc:
            return jsonify({"status": "error", "detail": str(exc)}), 500
        return jsonify({"status": "ok"})

    return app
