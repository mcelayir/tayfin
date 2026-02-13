"""Indicator repository — read-only access to tayfin_indicator.indicator_series."""

from __future__ import annotations

from sqlalchemy import text


def ping_db(engine) -> bool:
    """Execute ``SELECT 1`` to verify database connectivity."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1
