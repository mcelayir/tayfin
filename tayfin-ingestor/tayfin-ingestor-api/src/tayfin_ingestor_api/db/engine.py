import os
from sqlalchemy import create_engine


def get_engine():
    # Read DB connection info from env vars
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    db = os.getenv('DB_NAME', 'tayfin')
    user = os.getenv('DB_USER', 'tayfin')
    password = os.getenv('DB_PASS', '')

    url = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    engine = create_engine(url, future=True)
    return engine
