# Architecture Decision Record: Environment Variable Contract

## Status

**Proposed**

## Context

An audit of all 7 Tayfin services reveals inconsistent environment variable naming, driver strings, and dependency versions:

### Database Connection Variables

| Service | Host Var | Port Var | DB Var | User Var | Password Var |
|---|---|---|---|---|---|
| ingestor-api | `DB_HOST` | `DB_PORT` | `DB_NAME` | `DB_USER` | `DB_PASS` |
| indicator-api | `POSTGRES_HOST` | `POSTGRES_PORT` | `POSTGRES_DB` | `POSTGRES_USER` | `POSTGRES_PASSWORD` |
| screener-api | `POSTGRES_HOST` | `POSTGRES_PORT` | `POSTGRES_DB` | `POSTGRES_USER` | `POSTGRES_PASSWORD` |
| BFF | (no DB) | — | — | — | — |
| ingestor-jobs | `POSTGRES_HOST` | `POSTGRES_PORT` | `POSTGRES_DB` | `POSTGRES_USER` | `POSTGRES_PASSWORD` |
| indicator-jobs | `POSTGRES_HOST` | `POSTGRES_PORT` | `POSTGRES_DB` | `POSTGRES_USER` | `POSTGRES_PASSWORD` |
| screener-jobs | `POSTGRES_HOST` | `POSTGRES_PORT` | `POSTGRES_DB` | `POSTGRES_USER` | `POSTGRES_PASSWORD` |

**Problem:** ingestor-api uses `DB_*` as primary and falls back to `POSTGRES_*`. Every other service uses `POSTGRES_*` exclusively. This makes a single `.env` file impossible to share cleanly — Docker Compose needs one canonical set.

### SQLAlchemy Driver Strings

| Service | Driver String |
|---|---|
| ingestor-api | `postgresql://` (psycopg2 dialect) |
| indicator-api | `postgresql+psycopg://` (psycopg3 dialect) |
| screener-api | `postgresql+psycopg://` (psycopg3 dialect) |
| ingestor-jobs | `postgresql+psycopg://` |
| indicator-jobs | `postgresql+psycopg://` |
| screener-jobs | `postgresql+psycopg://` |

**Problem:** ingestor-api is the sole outlier using the psycopg2 driver.

### Python Package Versions

| Service | SQLAlchemy | psycopg Driver |
|---|---|---|
| ingestor-api | `>=1.4` | `psycopg2-binary>=2.9` |
| indicator-api | `>=2.0` | `psycopg[binary]>=3.1` |
| screener-api | `>=2.0` | `psycopg[binary]>=3.1` |
| BFF | — | — |
| ingestor-jobs | `>=2.0` | `psycopg[binary]>=3.1` |
| indicator-jobs | `>=2.0` | `psycopg[binary]>=3.1` |
| screener-jobs | `>=2.0` | `psycopg[binary]>=3.1` |

**Problem:** ingestor-api declares `SQLAlchemy>=1.4` and `psycopg2-binary>=2.9`, diverging from every other service.

### Inter-Service URL Variables

| Client | Variable | Default |
|---|---|---|
| indicator-api → ingestor-api | `TAYFIN_INGESTOR_API_BASE_URL` | `http://localhost:8000` |
| BFF → screener-api | `TAYFIN_SCREENER_API_BASE_URL` | `http://127.0.0.1:8020` |

**Problem:** Minor — `localhost` vs `127.0.0.1`. Both work, but Docker Compose needs service hostnames (e.g., `http://ingestor-api:8000`).

---

## Decision

### 1. Database Variables — Canonical Names

All services **MUST** use the `POSTGRES_*` prefix:

| Variable | Purpose | Example |
|---|---|---|
| `POSTGRES_HOST` | Database hostname | `localhost` / `db` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `tayfin` |
| `POSTGRES_USER` | Database user | `tayfin_user` |
| `POSTGRES_PASSWORD` | Database password | (see ADR-06) |

**Action:** ingestor-api must be migrated to `POSTGRES_*` with the `DB_*` fallback removed entirely.

**Rationale:** `POSTGRES_*` is already used by 6 of 7 services. It also aligns with the TimescaleDB/PostgreSQL container convention where `POSTGRES_USER` and `POSTGRES_PASSWORD` are the standard init variables.

### 2. Driver String — Canonical Value

All services **MUST** use:

```
postgresql+psycopg://
```

This selects the **psycopg3** async-capable driver, consistent with `psycopg[binary]>=3.1`.

**Action:** ingestor-api must be migrated from `postgresql://` to `postgresql+psycopg://`.

### 3. Python Packages — Canonical Versions

All services with database access **MUST** declare:

```
SQLAlchemy>=2.0
psycopg[binary]>=3.1
```

**Action:** ingestor-api `requirements.txt` must replace `SQLAlchemy>=1.4` and `psycopg2-binary>=2.9`.

### 4. Inter-Service URL Variables — Naming Convention

All inter-service base URL variables **MUST** follow this pattern:

```
TAYFIN_<TARGET_CONTEXT>_API_BASE_URL
```

Complete registry of inter-service URL variables:

| Variable | Used By | Docker Default | Local Default |
|---|---|---|---|
| `TAYFIN_INGESTOR_API_BASE_URL` | indicator-api | `http://ingestor-api:8000` | `http://localhost:8000` |
| `TAYFIN_INDICATOR_API_BASE_URL` | (future use) | `http://indicator-api:8010` | `http://localhost:8010` |
| `TAYFIN_SCREENER_API_BASE_URL` | BFF | `http://screener-api:8020` | `http://localhost:8020` |

**Defaults in code** remain `http://localhost:<port>` for local-without-Docker use. Docker Compose overrides these via environment block.

### 5. API Port Allocation — Canonical Registry

| Service | Port | Variable |
|---|---|---|
| ingestor-api | 8000 | `FLASK_PORT` (default: `8000`) |
| indicator-api | 8010 | `FLASK_PORT` (default: `8010`) |
| screener-api | 8020 | `FLASK_PORT` (default: `8020`) |
| BFF | 8030 | `FLASK_PORT` (default: `8030`) |
| UI (Vite) | 5173 | (Vite config) |

---

## Engine Template

All `db/engine.py` modules **MUST** converge to this template:

```python
"""SQLAlchemy engine factory — singleton, psycopg3 driver."""

import os
from sqlalchemy import create_engine, Engine

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "tayfin")
    user = os.environ.get("POSTGRES_USER", "tayfin_user")
    password = os.environ.get("POSTGRES_PASSWORD", "")

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    _engine = create_engine(url, future=True)
    return _engine
```

**Key properties:**

- Singleton pattern (all services except ingestor-api already do this)
- `postgresql+psycopg://` driver
- `POSTGRES_*` variables only
- `future=True` for SQLAlchemy 2.x forward compatibility
- Default password is empty string — see ADR-06 for local-dev policy

---

## Canonical `.env.example`

The root `.env.example` file must be updated to match:

```env
# === Database (shared by all DB-connected services) ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tayfin
POSTGRES_USER=tayfin_user
POSTGRES_PASSWORD=change_me

# === Inter-Service URLs (override for Docker Compose) ===
TAYFIN_INGESTOR_API_BASE_URL=http://localhost:8000
TAYFIN_INDICATOR_API_BASE_URL=http://localhost:8010
TAYFIN_SCREENER_API_BASE_URL=http://localhost:8020
```

---

## Consequences

- **ingestor-api** requires the most work: new env var names, new driver, new packages, singleton engine pattern.
- A single `.env` file at repo root can configure all services identically.
- Docker Compose can set `POSTGRES_HOST=db` and inter-service URLs to container hostnames in one environment block.
- Future services must follow this contract — no new variable naming schemes.
- The `DB_*` prefix is permanently retired.
