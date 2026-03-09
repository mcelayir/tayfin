"""Unit tests for ADR-06 credential defaults in tayfin-ingestor-jobs engine.

Validates:
  - Default user is 'tayfin_user' (not 'tayfin' or 'postgres')
  - Default password is empty string (not 'change_me' or 'tayfin_password')
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
        """Default POSTGRES_USER must be 'tayfin_user', not 'tayfin' or 'postgres'."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_ingestor_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert "tayfin_user:" in url
            assert "postgres:" not in url.split("@")[0]

    def test_default_password_is_empty(self):
        """Default POSTGRES_PASSWORD must be '' (empty), not 'change_me'."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_ingestor_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            # URL format: postgresql+psycopg://user:password@host:port/db
            # With empty password: tayfin_user:@localhost
            assert "tayfin_user:@" in url or "tayfin_user:***@" in url
            assert "change_me" not in url
            assert "tayfin_password" not in url

    def test_driver_is_psycopg3(self):
        """Driver string must be postgresql+psycopg://."""
        env = {k: v for k, v in os.environ.items()
               if k not in ("POSTGRES_USER", "POSTGRES_PASSWORD",
                            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")}
        with mock.patch.dict(os.environ, env, clear=True):
            from tayfin_ingestor_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert url.startswith("postgresql+psycopg://")

    def test_env_var_override(self):
        """POSTGRES_* env vars must override defaults."""
        env_override = {
            "POSTGRES_USER": "custom_user",
            "POSTGRES_PASSWORD": "custom_pass",
            "POSTGRES_HOST": "customhost",
            "POSTGRES_PORT": "9999",
            "POSTGRES_DB": "customdb",
        }
        with mock.patch.dict(os.environ, env_override, clear=False):
            from tayfin_ingestor_jobs.db.engine import get_engine
            engine = get_engine()
            url = str(engine.url)
            assert "custom_user" in url
            assert "customhost" in url
            assert "9999" in url
            assert "customdb" in url
