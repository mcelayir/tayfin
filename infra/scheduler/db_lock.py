
"""DB advisory lock helpers for scheduler and jobs.

Provides convenience functions to acquire/release PostgreSQL advisory locks
using a psycopg connection. The helpers expect an environment-configured
Postgres connection (see usage in `scheduler.py`).
"""
from typing import Optional
import os
import psycopg


def make_lock_key(name: str) -> int:
    # Simple stable hash to 32-bit signed int
    return abs(hash(name)) % (2 ** 31 - 1)


def _connect_from_env():
    host = os.environ.get("POSTGRES_HOST", "db")
    db = os.environ.get("POSTGRES_DB", "tayfin")
    user = os.environ.get("POSTGRES_USER", "tayfin_user")
    password = os.environ.get("POSTGRES_PASSWORD", "tayfin_password")
    conninfo = f"host={host} dbname={db} user={user} password={password}"
    return psycopg.connect(conninfo)


def get_connection():
    """Return a new psycopg connection using environment variables."""
    return _connect_from_env()


def try_acquire_lock(name: str, conn: Optional[psycopg.Connection] = None) -> bool:
    """Try to acquire an advisory lock for `name`. Returns True if acquired."""
    own_conn = False
    if conn is None:
        conn = _connect_from_env()
        own_conn = True
    key = make_lock_key(name)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s);", (key,))
            res = cur.fetchone()
            return bool(res and res[0])
    finally:
        if own_conn:
            conn.close()


def release_lock(name: str, conn: Optional[psycopg.Connection] = None) -> bool:
    """Release advisory lock for `name`. Returns True if unlocked."""
    own_conn = False
    if conn is None:
        conn = _connect_from_env()
        own_conn = True
    key = make_lock_key(name)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s);", (key,))
            res = cur.fetchone()
            return bool(res and res[0])
    finally:
        if own_conn:
            conn.close()
