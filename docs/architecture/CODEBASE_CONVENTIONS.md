# CODEBASE CONVENTIONS

This document codifies the **file placement and naming patterns** used across the Tayfin codebase.

These are not suggestions — they are the established conventions.
Any code generation tool (including AI assistants) MUST follow them exactly.

---

# 1. Jobs app structure (per context)

Each `*-jobs` app follows this layout:

```
tayfin-<context>/tayfin-<context>-jobs/
├── config/                          # YAML job configs
│   └── <domain>.yml                 # one per domain (discovery.yml, fundamentals.yml, ohlcv.yml)
├── scripts/                         # helper shell scripts
│   └── run_<domain>.sh              # one per domain
├── requirements.txt
├── README.md
├── tests/
└── src/tayfin_<context>_jobs/
    ├── __init__.py
    ├── __main__.py                  # entry point: imports cli/main.py
    ├── cli/
    │   └── main.py                  # Typer CLI (list, run)
    ├── config/
    │   └── loader.py                # YAML + env loader
    ├── db/
    │   └── engine.py                # SQLAlchemy engine factory
    ├── repositories/                # shared audit repositories
    │   ├── job_run_repository.py
    │   └── job_run_item_repository.py
    ├── jobs/                        # ← ALL job classes live here
    │   ├── discovery_job.py
    │   ├── fundamentals_job.py
    │   └── ohlcv_job.py
    └── <domain>/                    # domain packages (one per domain)
        ├── interfaces.py            # Protocol classes
        ├── factory.py               # provider factory
        ├── normalize.py             # normalization logic (if applicable)
        ├── providers/
        │   ├── base.py              # base classes / exceptions
        │   └── <name>_provider.py   # concrete providers
        └── repositories/
            └── <name>_repository.py # domain-specific repositories
```

---

# 2. Job files

## 2.1 Location

Job classes MUST live in `jobs/<domain>_job.py`.

**Never** place a job class inside the domain package.

```
✅  jobs/ohlcv_job.py
❌  ohlcv/job.py
❌  ohlcv/ohlcv_job.py
```

## 2.2 Naming

File: `<domain>_job.py`
Class: `<Domain>Job`

Examples:
- `discovery_job.py` → `DiscoveryJob`
- `fundamentals_job.py` → `FundamentalsJob`
- `ohlcv_job.py` → `OhlcvJob`

## 2.3 Import in CLI

The CLI imports jobs from `..jobs.<domain>_job`:

```python
from ..jobs.discovery_job import DiscoveryJob
from ..jobs.fundamentals_job import FundamentalsJob
from ..jobs.ohlcv_job import OhlcvJob
```

---

# 3. Domain packages

## 3.1 Purpose

Domain packages (`discovery/`, `fundamentals/`, `ohlcv/`) contain:
- providers (data fetching)
- repositories (domain-specific persistence)
- interfaces (Protocol classes)
- factories (provider construction)
- normalization logic

Domain packages MUST NOT contain job classes.

## 3.2 Provider naming

File: `<source>_provider.py`
Class: `<Source><Domain>Provider`

Examples:
- `stockdex_provider.py` → `StockdexProvider`
- `tradingview_provider.py` → `TradingViewOhlcvProvider`
- `yfinance_provider.py` → `YfinanceOhlcvProvider`
- `nasdaqtrader.py` → `NasdaqTraderIndexDiscoveryProvider`

## 3.3 Repository naming

File: `<entity>_repository.py`
Class: `<Entity>Repository`

Examples:
- `instrument_repository.py` → `InstrumentRepository`
- `ohlcv_repository.py` → `OhlcvRepository`
- `fundamentals_snapshot_repository.py` → `FundamentalsSnapshotRepository`

---

# 4. Config files

YAML configs live in `config/<domain>.yml`.

One file per domain. Keyed as `jobs.<domain>.<target-name>`.

```
config/discovery.yml        → jobs.discovery.nasdaq-100
config/fundamentals.yml     → jobs.fundamentals.nasdaq-100
config/ohlcv.yml            → jobs.ohlcv.nasdaq-100
```

---

# 5. Shell scripts

Helper scripts live in `scripts/run_<domain>.sh`.

Pattern:
1. Resolve `repo_root`
2. Source `.env`
3. Create/activate venv from `requirements.txt`
4. Export `PYTHONPATH`
5. Run `python -m tayfin_<context>_jobs jobs run <domain> <target> --config <path>`

Support `list` as first arg and pass through additional CLI flags.

---

# 6. Shared vs domain-specific repositories

Shared (audit) repositories live in the top-level `repositories/` folder:
- `job_run_repository.py`
- `job_run_item_repository.py`

Domain-specific repositories live inside the domain package:
- `discovery/repositories/instrument_repository.py`
- `fundamentals/repositories/fundamentals_snapshot_repository.py`
- `ohlcv/repositories/ohlcv_repository.py`

---

# 7. Migrations

Each context owns its migrations in `tayfin-<context>/db/migrations/`.

Naming: `V<N>__<description>.sql`

Migrations MUST only modify the owning context's schema.

---

# 8. When a stub or file already exists

If a file already exists (e.g. a stub), treat its location and name as a locked decision.

Replace its contents — do NOT move, rename, or relocate it.

---

# 9. Adding a new domain

When adding a new domain (e.g. `signals`), create:

1. `jobs/signals_job.py` — the job class
2. `signals/` — domain package with providers, repositories, etc.
3. `config/signals.yml` — YAML config
4. `scripts/run_signals.sh` — helper script
5. Wire into `cli/main.py` — add to `list` and `run` commands

Follow the exact patterns above. Do not invent new conventions.

---

This document is binding. When in doubt, look at the existing files and match them exactly.
