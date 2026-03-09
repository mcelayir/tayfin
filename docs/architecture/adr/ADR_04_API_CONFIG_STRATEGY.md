# Architecture Decision Record: API Configuration Strategy

## Status

**Proposed**

## Context

Tayfin's three **jobs** applications have a mature, consistent configuration pattern:

- `config/loader.py` module at the package level
- `python-dotenv` loaded at module import time via `load_dotenv()`
- YAML config file in `config/<domain>.yml`
- Precedence: CLI > env vars > YAML > defaults (TECH_STACK_RULES §2.1)

The four **API** services have evolved ad-hoc with no unified approach:

| Service | Config Loader | python-dotenv | YAML Config |
|---|---|---|---|
| ingestor-api | None | Not installed | None |
| indicator-api | None | Installed, never called | None |
| screener-api | None | Installed, never called | None |
| BFF | Exists (`config/__init__.py` + `config/loader.py`) | Installed, called at import | Exists (`bff.yml`) but **dead code** — `create_app()` never calls `load_config()` |

This inconsistency creates problems:

1. **Docker Compose difficulty** — Without `python-dotenv`, APIs can only receive config from shell-level env exports. Docker environment variables work, but local development without Docker relies on shell scripts sourcing `.env`.
2. **No YAML config for APIs** — APIs cannot be tuned via config files (e.g., timeouts, upstream URLs, pagination limits).
3. **BFF dead code** — The BFF has the right structure but `ScreenerClient` reads `os.environ` directly, ignoring the YAML layer entirely.
4. **Developer confusion** — Each API handles configuration differently, making onboarding harder.

This ADR decides the unified configuration approach for all API services.

---

## Options Considered

### Option A — Full Jobs Pattern (dotenv + YAML + env precedence)

**Description:** Every API gets a `config/loader.py` that calls `load_dotenv()` at import time and loads a YAML file. The loader returns the YAML dict; env vars override via `os.environ`.

**Template:**

```python
"""YAML + env config loader for <service>."""

from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(
    path: Path | None = None,
    default_filename: str = "<context>.yml",
) -> dict:
    cfg: dict = {}
    if path:
        p = Path(path)
    else:
        p = Path(__file__).resolve().parents[3] / "config" / default_filename
    if p.exists():
        with p.open("r") as f:
            cfg = yaml.safe_load(f) or {}
    return cfg
```

**Pros:**

- Identical pattern across all jobs and APIs — maximum consistency
- Supports YAML-based tuning (timeouts, limits, feature flags) without code changes
- `load_dotenv()` ensures `.env` works regardless of how the process is started
- Follows TECH_STACK_RULES §2 precedence: CLI > env > YAML > defaults

**Cons:**

- Adds `PyYAML` dependency to APIs that currently don't have it (indicator-api, screener-api, ingestor-api)
- YAML config files may go unused initially — APIs are simpler than jobs

### Option B — Env-Only (no YAML for APIs)

**Description:** APIs use only `python-dotenv` + `os.environ`. No YAML config files.

**Pros:**

- Simpler — fewer files, no YAML dependency
- Env vars are sufficient for the limited config APIs need (DB connection, upstream URLs)
- Docker Compose naturally provides env vars

**Cons:**

- Breaks consistency with jobs pattern
- No YAML layer for complex configuration (e.g., multiple upstream URLs with timeouts)
- `python-dotenv` alone doesn't match the established precedence model

### Option C — Extend BFF Pattern

**Description:** Use the existing BFF `config/__init__.py` style as the template for all APIs.

**Pros:**

- BFF already has a working (if dead) implementation
- Structurally similar to the jobs pattern

**Cons:**

- BFF's current implementation has a structural issue: `loader.py` is a re-export shim and `__init__.py` does the real work. This is backwards compared to the jobs convention where `loader.py` is the real module.
- The BFF pattern is effectively the same as Option A but with an unnecessary indirection layer.

---

## Decision

**Option A — Full Jobs Pattern** is adopted for all API services.

### Rationale

- Consistency is a first-class principle in Tayfin (ARCHITECTURE_RULES §8: "prefer explicitness over magic").
- The cost (adding PyYAML + a YAML file) is trivial compared to the benefit of having one configuration pattern across all 7+ services.
- YAML configs allow tuning API behavior (timeouts, pagination defaults, upstream URLs) without code changes or environment variable proliferation.
- The BFF already demonstrates the need for YAML-based upstream URL config — it just needs to be wired correctly.

---

## Implementation Guidelines

### Config Loader Module

Every API will have `src/<package>/config/loader.py` with the template from Option A.

The `config/__init__.py` file (if present) should import from `loader.py` for convenience:

```python
"""Config package — re-export loader for convenience."""

from .loader import load_config

__all__ = ["load_config"]
```

### YAML Config Files

Each API will have a `config/<context>.yml` file:

| Service | File | Key Settings |
|---|---|---|
| ingestor-api | `config/ingestor.yml` | (minimal — DB config is env-only) |
| indicator-api | `config/indicator.yml` | `upstream.ingestor_api_base_url`, `upstream.timeout_s` |
| screener-api | `config/screener.yml` | (minimal — read-only, no upstream calls) |
| BFF | `config/bff.yml` | `upstream.screener_api_base_url`, `upstream.timeout_s`, `upstream.max_retries` |

### Wiring into `app.py`

Each API's `create_app()` must call `load_config()` at init to ensure `load_dotenv()` runs:

```python
from .config.loader import load_config

def create_app() -> Flask:
    config = load_config()
    app = Flask(__name__)
    # config dict available for YAML-based settings
    # env vars available via os.environ (loaded by dotenv)
    ...
```

### Dependencies

All APIs must include in `requirements.txt`:

```
python-dotenv>=1.0
PyYAML>=6.0
```

---

## Consequences

- All 7 Tayfin services (3 jobs + 4 APIs) follow the same config pattern.
- `load_dotenv()` is called at import time in every service, ensuring `.env` files work in all execution modes (Docker, shell script, direct `python -m`).
- YAML config files provide a tuning layer without env var proliferation.
- The BFF's existing dead `load_config()` path is revived and becomes the standard.
- New services added in the future must follow this pattern.
