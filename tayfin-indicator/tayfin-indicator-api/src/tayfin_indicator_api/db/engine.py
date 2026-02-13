"""SQLAlchemy engine factory for tayfin-indicator-api."""

import os

from sqlalchemy import create_engine

_engine = None


def get_engine():
    """Return a singleton SQLAlchemy engine built from environment variables."""
    global _engine
    if _engine is not None:
        return _engine

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "tayfin")
    user = os.getenv("POSTGRES_USER", "tayfin_user")
    password = os.getenv("POSTGRES_PASSWORD", "")

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    _engine = create_engine(url, future=True)
    return _engine
