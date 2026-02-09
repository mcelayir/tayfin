from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: Path | None = None, default_filename: str = "discovery.yml") -> dict:
    """Load YAML config and return as dict. Precedence: CLI > env vars > YAML > defaults.

    This loader is minimal: it reads YAML and returns dict. Environment variables
    are available via os.environ for other code to consume.
    """
    cfg = {}
    if path:
        p = Path(path)
    else:
        # Default to the package-local config file under the job package root
        p = Path(__file__).resolve().parents[3] / "config" / default_filename
    if p.exists():
        with p.open("r") as f:
            cfg = yaml.safe_load(f) or {}
    return cfg
