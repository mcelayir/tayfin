"""YAML + env config loader for tayfin-indicator-jobs."""

from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: Path | None = None, default_filename: str = "indicator.yml") -> dict:
    """Load YAML config and return as dict.

    Precedence: CLI > env vars > YAML > defaults.
    Fallback order:
      1. explicit `path` argument
      2. directory from env `TAYFIN_CONFIG_DIR` (if set)
      3. container-mounted `/app/config/<default_filename>`
      4. package-relative `config/<default_filename>`
    """
    cfg: dict = {}
    # 1: explicit path
    if path:
        p = Path(path)
        if p.exists():
            with p.open("r") as f:
                return yaml.safe_load(f) or {}

    # 2: env-config dir
    env_dir = os.environ.get("TAYFIN_CONFIG_DIR")
    if env_dir:
        p = Path(env_dir) / default_filename
        if p.exists():
            with p.open("r") as f:
                return yaml.safe_load(f) or {}

    # 3: well-known container path
    p = Path("/app/config") / default_filename
    if p.exists():
        with p.open("r") as f:
            return yaml.safe_load(f) or {}

    # 4: package-local config
    p = Path(__file__).resolve().parents[3] / "config" / default_filename
    if p.exists():
        with p.open("r") as f:
            cfg = yaml.safe_load(f) or {}
    return cfg
