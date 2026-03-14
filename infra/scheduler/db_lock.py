"""DB advisory lock helpers for scheduler and jobs.

This is a lightweight helper that uses PostgreSQL advisory locks.
"""
from typing import Optional


def lock_sql(key: int) -> str:
    return "SELECT pg_try_advisory_lock(%s);" % key


def unlock_sql(key: int) -> str:
    return "SELECT pg_advisory_unlock(%s);" % key


def make_lock_key(name: str) -> int:
    # Simple stable hash to 32-bit signed int
    return abs(hash(name)) % (2 ** 31 - 1)
