"""SQLAlchemy engine singleton for tayfin-screener-api."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

_engine = None


def get_engine():
    """Build (or reuse) a SQLAlchemy engine from environment variables."""
    global _engine
    if _engine is not None:
        return _engine
    user = os.getenv("POSTGRES_USER", "tayfin_user")
    password = os.getenv("POSTGRES_PASSWORD", "tayfin_password")
    db = os.getenv("POSTGRES_DB", "tayfin")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    _engine = create_engine(url, future=True)
    return _engine
