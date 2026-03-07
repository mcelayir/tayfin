"""Tests for tayfin_screener_jobs.config.loader."""

from __future__ import annotations

from pathlib import Path

from tayfin_screener_jobs.config.loader import load_config


class TestLoadConfig:
    """Tests for :func:`load_config`."""

    def test_loads_default_screener_yml(self):
        """Default config path should resolve to config/screener.yml."""
        cfg = load_config()
        # Should contain our jobs.vcp_screen configuration
        assert "jobs" in cfg
        assert "vcp_screen" in cfg["jobs"]

    def test_loads_explicit_path(self, tmp_path):
        p = tmp_path / "test.yml"
        p.write_text("jobs:\n  my_job:\n    x: 1\n")
        cfg = load_config(path=p)
        assert cfg["jobs"]["my_job"]["x"] == 1

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.yml"
        cfg = load_config(path=p)
        assert cfg == {}

    def test_empty_yaml_returns_empty(self, tmp_path):
        p = tmp_path / "empty.yml"
        p.write_text("")
        cfg = load_config(path=p)
        assert cfg == {}

    def test_vcp_screen_has_targets(self):
        cfg = load_config()
        targets = cfg["jobs"]["vcp_screen"]["targets"]
        assert "nasdaq-100" in targets
        target = targets["nasdaq-100"]
        assert target["index_code"] == "NDX"
        assert "indicators" in target

    def test_indicators_list(self):
        cfg = load_config()
        indicators = cfg["jobs"]["vcp_screen"]["targets"]["nasdaq-100"]["indicators"]
        keys = [i["key"] for i in indicators]
        assert "sma" in keys
        assert "atr" in keys
        assert "vol_sma" in keys
        assert "rolling_high" in keys
