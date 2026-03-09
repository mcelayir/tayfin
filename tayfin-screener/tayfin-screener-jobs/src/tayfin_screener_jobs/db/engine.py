"""SQLAlchemy engine factory for tayfin-screener-jobs.

Env var contract per ADR-05: POSTGRES_* only, postgresql+psycopg:// driver.
Default credentials per ADR-06: tayfin_user / empty password.
"""

import os

from sqlalchemy import create_engine


def get_engine():
    """Build a SQLAlchemy engine from environment variables."""
    user = os.environ.get("POSTGRES_USER", "tayfin_user")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "tayfin")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)
