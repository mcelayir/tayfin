from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: Path | None = None) -> dict:
    """Load YAML config and return as dict. Precedence: CLI > env vars > YAML > defaults.

    This loader is minimal: it reads YAML and returns dict. Environment variables
    are available via os.environ for other code to consume.
    """
    cfg = {}
    if path:
        p = Path(path)
    else:
        # Default to the package-local config file under the job package root:
        # tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml
        p = Path(__file__).resolve().parents[3] / "config" / "discovery.yml"
    if p.exists():
        with p.open("r") as f:
            cfg = yaml.safe_load(f) or {}
    return cfg
