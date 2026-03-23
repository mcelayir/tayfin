# tayfin-indicator

## Description
Computes technical indicators (SMA, ATR, volatility SMA, rolling Highs, etc.) from OHLCV series and persists indicator series for downstream consumers and APIs.

## Service Overview
- Responsibility: Calculation Logic and persistence of indicator series
- Primary interfaces: `tayfin-indicator-api` (read-only HTTP API), `tayfin-indicator-jobs` (Typer CLI jobs)
- Owner: @dev

## Getting Started

### Local Commands
| Task | Command | Description |
| :--- | :--- | :--- |
| Start API (helper) | `bash tayfin-indicator/tayfin-indicator-api/scripts/run_api.sh` | Starts the read-only API on port 8010 (loads .env if present). |
| Run job (example) | `python -m tayfin_indicator_jobs jobs run ma_compute nasdaq-100 --config tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml` | Run configured indicator job (uses Typer CLI). |
| List jobs | `python -m tayfin_indicator_jobs jobs list --config tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml` | List configured jobs and targets. |
| Run tests | `pytest -q` | Run unit tests for the module (subpackages have their own requirements). |

### Environment Variables
| Key | Type | Required | Default | Example | Notes |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `POSTGRES_HOST` | string | Yes | `localhost` | `localhost` | Database host for indicator persistence |
| `POSTGRES_PORT` | integer | Yes | `5432` | `5432` | Database port |
| `POSTGRES_DB` | string | Yes | `tayfin` | `tayfin` | Database name |
| `POSTGRES_USER` | string | Yes | `tayfin_user` | `tayfin_user` | DB user |
| `POSTGRES_PASSWORD` | string | Conditionally | _(empty)_ | `REDACTED` | DB password (do not commit secrets) |
| `JOB_RUN_ID` | string | Yes | - | `job-20260322-abc123` | Job provenance identifier attached to writes; include as `created_by_job_run_id` on persistent writes |
| `TAYFIN_INGESTOR_API_BASE_URL` | string | Conditionally | `http://localhost:8000` | `http://localhost:8000` | Upstream ingestor API base used to fetch OHLCV/index members |

Notes:
- Prefer loading environment variables from the repo root `.env` for local development.  
- Never commit real secrets; use placeholders like `REDACTED`.

## Local Jobs / Cron
- Jobs are configured in `tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml` and executed via the Typer CLI (see `tayfin_indicator_jobs.cli.main`).

## API Documentation
See `tayfin-indicator/tayfin-indicator-api/README.md` for endpoint examples and payload shapes (includes `GET /indicators/latest`, `GET /indicators/range`, and index-level endpoints).

## Request / Response Types
- Canonical response examples and serializers live under `tayfin-indicator/tayfin-indicator-api/src/tayfin_indicator_api/serializers/` and should be used as the source of truth when producing examples.

## Observability
- Logs: include `job_run_id` in job flows and repository writes.  
- Metrics: exported by API and jobs (instrumentation varies by service).

## QA Checklist
- [ ] Curl examples in `tayfin-indicator-api/README.md` run against a local dev instance.  
- [ ] Jobs example runs locally and writes indicator rows to `indicator_series` table.  
- [ ] Env var table is complete and accurate.  
- [ ] No secrets in this README.

## Links
- Code: `tayfin-indicator`  
- Jobs config: `tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml`  
- API README: `tayfin-indicator/tayfin-indicator-api/README.md`

## CHANGELOG
- 2026-03-23: initial draft (E36-04.2) by @dev
# tayfin-indicator

Bounded context for **technical-indicator computation and storage**.

## Sub-applications

| App | Purpose |
|-----|---------|
| `tayfin-indicator-jobs` | CLI / scheduled jobs that compute indicators |
| `tayfin-indicator-api`  | Read-only REST API exposing computed indicators |

## Database

Flyway-managed migrations live in `db/migrations/`.
Schema: `indicator` (created by the init migration).
