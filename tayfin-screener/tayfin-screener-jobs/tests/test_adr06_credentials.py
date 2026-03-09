"""Unit tests for ADR-06 credential defaults in tayfin-screener-jobs engine.

Validates:
  - Default user is 'tayfin_user' (not 'postgres')
  - Default password is empty string (not 'tayfin_password')
  - Engine uses POSTGRES_* env vars
  - Driver is postgresql+psycopg://
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Ensure src/ is importable
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


class TestADR06Defaults:
    """ADR-06: all services must default to tayfin_user / empty password."""

    def test_default_user_is_tayfin_user(self):
        """Default POSTGRES_USER must be 'tayfin_user'."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_screener_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert "tayfin_user:" in url

    def test_default_password_is_empty(self):
        """Default POSTGRES_PASSWORD must be '' (empty), not 'tayfin_password'."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_screener_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            # With empty password: tayfin_user:@localhost (or :***@ if masked)
            assert "tayfin_user:@" in url or "tayfin_user:***@" in url
            assert "tayfin_password" not in url

    def test_driver_is_psycopg3(self):
        """Driver string must be postgresql+psycopg://."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_screener_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert url.startswith("postgresql+psycopg://")

    def test_env_var_override(self):
        """POSTGRES_* env vars must override defaults."""
        env_override = {
            "POSTGRES_USER": "override_user",
            "POSTGRES_PASSWORD": "override_pass",
            "POSTGRES_HOST": "override_host",
            "POSTGRES_PORT": "7777",
            "POSTGRES_DB": "override_db",
        }
        with mock.patch.dict(os.environ, env_override, clear=False):
            from tayfin_screener_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert "override_user" in url
            assert "override_host" in url
            assert "7777" in url
            assert "override_db" in url
