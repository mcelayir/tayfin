"""Shared pytest fixtures for tayfin-bff tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is importable when running tests from the tests/ folder.
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
