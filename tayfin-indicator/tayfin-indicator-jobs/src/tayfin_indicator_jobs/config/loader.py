"""YAML + env config loader for tayfin-indicator-jobs."""

from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: Path | None = None, default_filename: str = "indicator.yml") -> dict:
    """Load YAML config and return as dict.

    Precedence: CLI > env vars > YAML > defaults.
    This loader reads YAML and returns a dict. Environment variables are
    available via ``os.environ`` for other code to consume.
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
