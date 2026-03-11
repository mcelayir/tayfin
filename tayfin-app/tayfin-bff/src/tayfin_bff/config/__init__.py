"""Config package for tayfin-bff — re-exports from loader (ADR-04)."""

from .loader import load_config

__all__ = ["load_config"]
