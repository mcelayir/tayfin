"""YAML + env config loader for tayfin-bff.

The BFF owns no database — it only needs upstream API URLs and a few
runtime knobs.  Environment variables take precedence over YAML values.

Follows ADR-04 pattern: dotenv loaded at import time, YAML read on demand.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(
    path: Path | None = None,
    default_filename: str = "bff.yml",
) -> dict:
    """Load YAML config and return the raw YAML dict.

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
