"""SQLAlchemy engine factory — singleton, psycopg3 driver.

Env var contract per ADR-05: POSTGRES_* only, postgresql+psycopg:// driver.
Default credentials per ADR-06: tayfin_user / empty password.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy engine built from environment variables."""
    global _engine
    if _engine is not None:
        return _engine

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "tayfin")
    user = os.environ.get("POSTGRES_USER", "tayfin_user")
    password = os.environ.get("POSTGRES_PASSWORD", "")

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    _engine = create_engine(url, future=True)
    return _engine


def reset_engine() -> None:
    """Dispose and clear the cached engine (for testing)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
