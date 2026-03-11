"""DB package — re-export engine for backward compatibility.

The engine implementation lives in db/engine.py per ADR-05.
Existing imports like ``from tayfin_screener_api.db import get_engine``
continue to work.
"""

from .engine import get_engine, reset_engine

__all__ = ["get_engine", "reset_engine"]
