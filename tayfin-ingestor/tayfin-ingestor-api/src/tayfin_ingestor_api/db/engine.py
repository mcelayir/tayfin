import os
from sqlalchemy import create_engine


def get_engine():
    # Read DB connection info from env vars
    host = os.getenv('DB_HOST', os.getenv('POSTGRES_HOST', 'localhost'))
    port = os.getenv('DB_PORT', os.getenv('POSTGRES_PORT', '5432'))
    db = os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'tayfin'))
    user = os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'tayfin'))
    password = os.getenv('DB_PASS', os.getenv('POSTGRES_PASSWORD', ''))

    url = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    engine = create_engine(url, future=True)
    return engine
