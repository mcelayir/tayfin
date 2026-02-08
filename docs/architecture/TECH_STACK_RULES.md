# TECH STACK RULES

This document defines the **project-wide tech stack and tooling rules** that guide implementation.
These rules exist to keep all apps consistent and Copilot-aligned.

---

# 1 Python baseline

* All Python apps MUST target **Python 3.11**.
* Each Python app MUST have its own dependencies (bounded context separation):

  * `requirements.txt`
  * (optional) `requirements-dev.txt`

**Example**

* `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`
* `tayfin-ingestor/tayfin-ingestor-api/requirements.txt`

---

# 2 Configuration

## 2.1 Sources and precedence

Configuration MUST be resolved in this order (later overrides earlier):

1. code defaults
2. YAML config file
3. environment variables (including values loaded from `.env` in dev)
4. CLI flags

In short:
**CLI > env vars > YAML > defaults**

## 2.2 .env usage

* `.env` is allowed and encouraged for **local development**.
* `.env` MUST NOT be required for production (production uses real env vars).

## 2.3 YAML job config

* Jobs MUST support a YAML config file passed via CLI (`--config`).
* Date parameters in YAML MUST be optional:

  * `start_date` optional
  * `end_date` optional
* `as_of_date` SHOULD NOT be required.

**Example YAML**

```yaml
jobs:
  nasdaq-fundamentals:
    market: NASDAQ
    country: US
    provider: stockdex
    start_date: 2026-01-01   # optional
    end_date: 2026-02-08     # optional
```

**Interpretation**

* If both dates omitted: job uses a sensible default (e.g., latest snapshot).
* If only start_date provided: job runs from start_date to "today".
* If both provided: job runs for the given range.

---

# 3 Jobs CLI tooling

* All `*-jobs` apps MUST use **Typer** for the CLI.
* CLI MUST support:

  * `jobs list`
  * `jobs run <job_name> --config <path>`
* Jobs must remain schedule-agnostic:

  * CLI runs once
  * schedulers (later) simply invoke the same CLI entrypoint

**Example commands**

```bash
python -m tayfin_ingestor_jobs jobs list
python -m tayfin_ingestor_jobs jobs run nasdaq-fundamentals --config config/dev.yml
```

---

# 4 Database access

## 4.1 Standard

* SQL access MUST use **SQLAlchemy Core** as the standard approach.
* DB access MUST be behind repositories (jobs orchestrate; repositories persist).

## 4.2 psycopg exception

* Direct `psycopg` usage is allowed only with **explicit justification**.
* The justification MUST be documented in the module README or code comment near the usage.

Allowed reasons include:

* bulk-copy performance (COPY)
* special PostgreSQL features not reasonably supported by current Core approach
* critical hot-path performance proven by measurement

---

# 5 HTTP client

* Outbound HTTP calls MUST use **httpx**.
* Timeouts MUST be set explicitly (no infinite defaults).
* Retries (if used) MUST be explicit and bounded.

---

# 6 APIs

* Flask is the default API framework for Python APIs.
* APIs MUST remain read-only over precomputed data and report artifacts.

---

# 7 Logging

* Python apps MUST use the standard `logging` module (no `print()` for operational logs).
* Jobs logs SHOULD include `job_run_id` in log context where available.
* Structured logging (JSON) is allowed and recommended, but not required immediately.

---

# 8 Linting & formatting

* Python apps SHOULD use `ruff` for linting and formatting.
* Keep configuration consistent, but it may be per-app to preserve bounded contexts.

---

This document is binding for implementation decisions unless explicitly changed.
