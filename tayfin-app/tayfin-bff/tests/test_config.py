"""Unit tests for BFF config loader (ADR-04 compliance) and app wiring.

Covers:
  - Config loader reads YAML files correctly
  - Config package re-exports load_config from loader module
  - load_config() is called and upstream config is wired in create_app()
  - BFF has NO database engine (architecture compliance)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

import yaml


# ── Config Loader ────────────────────────────────────────────────────


class TestConfigLoader:
    """Tests for config/loader.py — ADR-04 pattern."""

    def test_load_config_returns_dict(self):
        from tayfin_bff.config.loader import load_config

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as f:
            yaml.dump({"server": {"port": 8030}}, f)
            f.flush()
            cfg = load_config(path=Path(f.name))
        os.unlink(f.name)
        assert isinstance(cfg, dict)
        assert cfg["server"]["port"] == 8030

    def test_load_config_reads_yaml(self):
        from tayfin_bff.config.loader import load_config

        data = {"upstream": {"screener_api_base_url": "http://test:9999"}}
        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            cfg = load_config(path=Path(f.name))
        os.unlink(f.name)
        assert cfg["upstream"]["screener_api_base_url"] == "http://test:9999"

    def test_load_config_empty_yaml_returns_empty_dict(self):
        from tayfin_bff.config.loader import load_config

        with tempfile.NamedTemporaryFile(suffix=".yml", mode="w", delete=False) as f:
            f.write("")
            f.flush()
            cfg = load_config(path=Path(f.name))
        os.unlink(f.name)
        assert cfg == {}

    def test_load_config_missing_file_returns_empty_dict(self):
        from tayfin_bff.config.loader import load_config

        cfg = load_config(path=Path("/tmp/nonexistent_bff_test.yml"))
        assert cfg == {}


# ── Config Package Re-export ─────────────────────────────────────────


class TestConfigPackage:
    """Verify config/__init__.py re-exports from loader (ADR-04 structure)."""

    def test_config_package_reexport(self):
        from tayfin_bff.config import load_config as from_pkg
        from tayfin_bff.config.loader import load_config as from_loader

        assert from_pkg is from_loader

    def test_loader_module_contains_logic(self):
        """The loader module should contain the actual load_config body,
        not just a re-export."""
        import inspect
        from tayfin_bff.config.loader import load_config

        source = inspect.getsource(load_config)
        assert "yaml.safe_load" in source


# ── App Wiring ───────────────────────────────────────────────────────


class TestAppWiring:
    """Verify create_app() calls load_config() and feeds upstream config."""

    def test_create_app_calls_load_config(self):
        """load_config() must be called inside create_app()."""
        with mock.patch(
            "tayfin_bff.app.load_config",
            return_value={"upstream": {"screener_api_base_url": "http://mock:1234"}},
        ) as mocked:
            from tayfin_bff.app import create_app

            # Reset module-level client singleton to force fresh init
            import tayfin_bff.app as app_mod
            app_mod._client_instance = None

            app = create_app()
            mocked.assert_called_once()

    def test_upstream_config_passed_to_screener_client(self):
        """ScreenerClient must receive upstream config from bff.yml."""
        upstream = {
            "screener_api_base_url": "http://custom-screener:9090",
            "timeout_s": 15.0,
            "max_retries": 5,
        }
        with mock.patch(
            "tayfin_bff.app.load_config",
            return_value={"upstream": upstream},
        ):
            import tayfin_bff.app as app_mod
            app_mod._client_instance = None  # reset singleton

            app = app_mod.create_app()

            client = app_mod._screener_client()
            assert client.base_url == "http://custom-screener:9090"
            assert client.timeout == __import__("httpx").Timeout(15.0)
            assert client.max_retries == 5

            # Clean up
            app_mod._client_instance = None


# ── Architecture Compliance ──────────────────────────────────────────


class TestArchitectureCompliance:
    """BFF must NOT have a database — pure HTTP proxy."""

    def test_no_db_module(self):
        """BFF should not have a db/ package."""
        bff_src = Path(__file__).resolve().parents[1] / "src" / "tayfin_bff"
        db_dir = bff_src / "db"
        assert not db_dir.exists(), "BFF must not have a db/ module (§2.1)"

    def test_no_sqlalchemy_in_requirements(self):
        """requirements.txt must not contain sqlalchemy."""
        req_path = Path(__file__).resolve().parents[1] / "requirements.txt"
        content = req_path.read_text().lower()
        assert "sqlalchemy" not in content, "BFF must not depend on SQLAlchemy"

    def test_no_engine_import_in_app(self):
        """app.py must not import get_engine or create_engine."""
        import inspect
        from tayfin_bff import app as app_mod

        source = inspect.getsource(app_mod)
        assert "get_engine" not in source
        assert "create_engine" not in source
