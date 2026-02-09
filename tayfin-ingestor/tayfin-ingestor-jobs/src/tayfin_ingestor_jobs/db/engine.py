import os
from sqlalchemy import create_engine


def get_engine():
    user = os.environ.get("POSTGRES_USER", "tayfin")
    password = os.environ.get("POSTGRES_PASSWORD", "change_me")
    db = os.environ.get("POSTGRES_DB", "tayfin")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)
