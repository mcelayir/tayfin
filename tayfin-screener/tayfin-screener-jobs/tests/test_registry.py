"""Tests for tayfin_screener_jobs.jobs.registry."""

from __future__ import annotations

import pytest

from tayfin_screener_jobs.jobs.registry import _REGISTRY, get_job_class


class TestRegistry:
    """Tests for :func:`get_job_class`."""

    def test_vcp_screen_registered(self):
        assert "vcp_screen" in _REGISTRY

    def test_mcsa_screen_registered(self):
        assert "mcsa_screen" in _REGISTRY

    def test_get_job_class_returns_class(self):
        cls = get_job_class("vcp_screen")
        assert cls.__name__ == "VcpScreenJob"
        assert hasattr(cls, "from_config")
        assert hasattr(cls, "run")

    def test_get_mcsa_job_class(self):
        cls = get_job_class("mcsa_screen")
        assert cls.__name__ == "McsaScreenJob"
        assert hasattr(cls, "from_config")
        assert hasattr(cls, "run")

    def test_unknown_job_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown job"):
            get_job_class("nonexistent_job")

    def test_registry_entry_format(self):
        """Every registry entry must be 'module.ClassName' format."""
        for name, entry in _REGISTRY.items():
            parts = entry.rsplit(".", 1)
            assert len(parts) == 2, f"Bad registry entry for {name}: {entry}"
            assert parts[1][0].isupper(), f"Class name should be PascalCase: {entry}"
