"""Unit tests for tayfin-indicator-api config & engine standardization.

Tests cover ADR-04 (config loader), ADR-05 (env var contract), and
ADR-06 (default credential policy).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest


# ================================================================
# A) Config Loader Tests (ADR-04)
# ================================================================


class TestConfigLoader:
    """Tests for config/loader.py."""

    def test_load_config_returns_dict(self, tmp_path: Path):
        """load_config() returns a dict even when YAML file is missing."""
        from tayfin_indicator_api.config.loader import load_config

        result = load_config(path=tmp_path / "nonexistent.yml")
        assert isinstance(result, dict)
        assert result == {}

    def test_load_config_reads_yaml(self, tmp_path: Path):
        """load_config() reads and parses a YAML file when present."""
        from tayfin_indicator_api.config.loader import load_config

        yml = tmp_path / "test.yml"
        yml.write_text(
            "server:\n  host: 0.0.0.0\n  port: 8010\n"
            "upstream:\n  ingestor_api_base_url: http://localhost:8000\n"
        )

        result = load_config(path=yml)
        assert result["server"]["port"] == 8010
        assert result["upstream"]["ingestor_api_base_url"] == "http://localhost:8000"

    def test_load_config_empty_yaml_returns_empty_dict(self, tmp_path: Path):
        """load_config() returns {} for an empty YAML file."""
        from tayfin_indicator_api.config.loader import load_config

        yml = tmp_path / "empty.yml"
        yml.write_text("")

        result = load_config(path=yml)
        assert result == {}

    def test_config_package_reexport(self):
        """config/__init__.py re-exports load_config."""
        from tayfin_indicator_api.config import load_config as from_init
        from tayfin_indicator_api.config.loader import load_config as from_loader

        assert from_init is from_loader


# ================================================================
# B) Engine Tests (ADR-05 / ADR-06)
# ================================================================


class TestUpstreamWiring:
    """Tests for create_app() wiring YAML upstream config into IngestorClient."""

    def test_yaml_upstream_applies_when_env_absent(self, monkeypatch, tmp_path):
        """YAML upstream.ingestor_api_base_url is applied when env var is not set."""
        # Ensure env var is absent
        monkeypatch.delenv("TAYFIN_INGESTOR_API_BASE_URL", raising=False)

        # Stub out IngestorClient, get_engine, and repo functions
        monkeypatch.setattr(
            "tayfin_indicator_api.app.get_engine", lambda: "fake-engine"
        )
        monkeypatch.setattr(
            "tayfin_indicator_api.app.ping_db", lambda engine: True
        )

        from tayfin_indicator_api.app import create_app

        app = create_app()

        assert app.config["INGESTOR_BASE_URL"] == "http://localhost:8000"
        assert app.config["INGESTOR_TIMEOUT_S"] == 30.0

    def test_env_var_overrides_yaml_upstream(self, monkeypatch):
        """TAYFIN_INGESTOR_API_BASE_URL env var overrides YAML value."""
        monkeypatch.setenv("TAYFIN_INGESTOR_API_BASE_URL", "http://ingestor-api:8000")

        monkeypatch.setattr(
            "tayfin_indicator_api.app.get_engine", lambda: "fake-engine"
        )
        monkeypatch.setattr(
            "tayfin_indicator_api.app.ping_db", lambda engine: True
        )

        from tayfin_indicator_api.app import create_app

        app = create_app()

        assert app.config["INGESTOR_BASE_URL"] == "http://ingestor-api:8000"


class TestGetEngine:
    """Tests for db/engine.py."""

    def setup_method(self):
        """Reset the engine singleton before each test."""
        from tayfin_indicator_api.db.engine import reset_engine

        reset_engine()

    def teardown_method(self):
        """Clean up the engine singleton after each test."""
        from tayfin_indicator_api.db.engine import reset_engine

        reset_engine()

    def test_get_engine_returns_engine(self):
        """get_engine() returns a SQLAlchemy Engine instance."""
        from sqlalchemy import Engine

        from tayfin_indicator_api.db.engine import get_engine

        engine = get_engine()
        assert isinstance(engine, Engine)

    def test_singleton_returns_same_instance(self):
        """get_engine() returns the same object on subsequent calls."""
        from tayfin_indicator_api.db.engine import get_engine

        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2

    def test_reset_engine_clears_singleton(self):
        """reset_engine() clears the cached engine."""
        from tayfin_indicator_api.db.engine import get_engine, reset_engine

        e1 = get_engine()
        reset_engine()
        e2 = get_engine()
        assert e1 is not e2

    def test_default_credentials_match_adr06(self):
        """Default env vars match ADR-06: tayfin_user / empty password."""
        from tayfin_indicator_api.db.engine import get_engine, reset_engine

        env_patch = {
            k: v for k, v in os.environ.items()
            if not k.startswith("POSTGRES_")
        }
        with mock.patch.dict(os.environ, env_patch, clear=True):
            reset_engine()
            engine = get_engine()
            url = str(engine.url)

            assert "tayfin_user" in url, f"Expected tayfin_user in URL, got: {url}"
            assert "localhost" in url
            assert "5432" in url
            assert "/tayfin" in url

    def test_driver_is_psycopg3(self):
        """Engine uses postgresql+psycopg:// driver per ADR-05."""
        from tayfin_indicator_api.db.engine import get_engine

        engine = get_engine()
        url = str(engine.url)
        assert url.startswith("postgresql+psycopg://"), (
            f"Expected postgresql+psycopg:// driver, got: {url}"
        )

    def test_postgres_env_vars_override_defaults(self):
        """POSTGRES_* env vars override the default values."""
        from tayfin_indicator_api.db.engine import get_engine, reset_engine

        custom_env = {
            "POSTGRES_HOST": "custom-host",
            "POSTGRES_PORT": "9999",
            "POSTGRES_DB": "custom_db",
            "POSTGRES_USER": "custom_user",
            "POSTGRES_PASSWORD": "secret",
        }
        with mock.patch.dict(os.environ, custom_env):
            reset_engine()
            engine = get_engine()
            url = str(engine.url)

            assert "custom-host" in url
            assert "9999" in url
            assert "custom_db" in url
            assert "custom_user" in url
