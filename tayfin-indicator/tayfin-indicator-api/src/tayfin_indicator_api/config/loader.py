"""YAML + env config loader for tayfin-indicator-api.

Follows the ADR-04 standard: python-dotenv at import time, YAML config
with env-var overrides.  Precedence: CLI > env vars > YAML > defaults.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(
    path: Path | None = None,
    default_filename: str = "indicator.yml",
) -> dict:
    """Load YAML config and return the raw dict.

    Environment variables are loaded into ``os.environ`` via ``python-dotenv``
    at module import time.  Callers should read ``os.environ`` directly for
    env-based overrides — this function only returns the YAML layer.
    """
    cfg: dict = {}
    if path:
        p = Path(path)
    else:
        p = Path(__file__).resolve().parents[3] / "config" / default_filename
    if p.exists():
        with p.open("r") as f:
            cfg = yaml.safe_load(f) or {}
    return cfg
