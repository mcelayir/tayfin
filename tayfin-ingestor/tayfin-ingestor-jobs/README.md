---
template_version: 1
module: tayfin-ingestor-jobs
owner: "@dev"
qa_checklist: true
---

# tayfin-ingestor-jobs

This package contains CLI-driven ingestion jobs for discovery, fundamentals, and OHLCV data.

## Getting Started

### Entrypoints
- CLI entrypoint: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/cli/main.py`  
- Module runnable: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/__main__.py`

### Local Commands / Scripts
| Task | Command | Description |
| :--- | :--- | :--- |
| Run discovery job | `./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_discovery.sh` | Discover instruments and upsert `instruments` + `index_memberships` |
| Run fundamentals job | `./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_fundamentals.sh` | Fetch daily fundamentals snapshots |
| Run OHLCV job | `./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh` | Fetch daily OHLCV candles (TradingView primary, yfinance fallback) |
| Run OHLCV backfill | `./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv_backfill.sh` | Backfill historical candles |

### Environment Variables (jobs)
| Key | Type | Required | Default | Example | Notes |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `DB_URL` | string | Yes | - | `postgres://user:pass@localhost:5432/tayfin` | Database used by jobs |
| `JOB_RUN_ID` | string | Yes | - | `job-20260322-abc123` | Must be provided/attached for job provenance writes; the `job_run_repository` records runs |
| `TRADINGVIEW_COOKIE` | string | Conditionally | - | `REDACTED` | Optional: authenticated cookie to extend TradingView rate limits |
| `OHLCV_RATE_LIMIT_RPS` | int | No | `5` | `5` | Rate limit tuning for providers |
| `OHLCV_RETRY_MAX_ATTEMPTS` | int | No | `3` | `3` | Retry attempts for provider requests |

Notes: jobs load config from `tayfin-ingestor/tayfin-ingestor-jobs/config/*.yml` — ensure values are consistent with env vars for local runs.

## Jobs Overview

- `discovery_job` (`jobs/discovery_job.py`): resolves index memberships and instruments. Use `run_discovery.sh` to execute.  
- `fundamentals_job` (`jobs/fundamentals_job.py`): fetches daily fundamentals snapshots using configured providers.  
- `ohlcv_job` (`jobs/ohlcv_job.py`): primary ingest job for daily OHLCV. Supports `--ticker`, `--from`, `--to`, and `--limit` options.  
- `ohlcv_backfill_job` (`jobs/ohlcv_backfill_job.py`): backfill historical ranges across tickers.

## Implementation Links

- CLI: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/cli/main.py`  
- Job implementations: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/`  
- Providers: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/*/providers/`  
- Job run repository: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/repositories/job_run_repository.py`

## Execution Examples

Run full OHLCV for NDX (example):
```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh
```

Run single ticker:
```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh --ticker AAPL
```

Backfill range:
```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv_backfill.sh --from 2020-01-01 --to 2020-12-31
```

## Observability

- Jobs write audit rows to `job_runs` and `job_run_items` tables; ensure `JOB_RUN_ID` is present.
- Log format: include `job_run_id`, `job_name`, and `provider` where applicable.  
- Metrics: emit `job_runs_total`, `job_run_success_total`, `job_run_failure_total` with `job_name` and `provider` tags.

## QA Checklist
- [ ] Run `run_ohlcv.sh` locally (with small `--limit`) and verify `job_runs` row created.  
- [ ] Run `run_fundamentals.sh` and inspect snapshot writes.  
- [ ] Run `run_discovery.sh` and validate `instruments` upserts.  
- [ ] Verify `JOB_RUN_ID` is recorded in `job_run_items` for each write.

## Troubleshooting

- DB connection failures: confirm `DB_URL` reachable and migrations applied (`tayfin-ingestor/db/migrations`).  
- Provider rate limits: configure `TRADINGVIEW_COOKIE` or tune `OHLCV_RATE_LIMIT_RPS`.

## CHANGELOG
- 2026-03-22 — Initial jobs README created (@dev)

---

Next: implement E36-03.5 (populate env var details across READMEs), E36-03.6 (add validation header to any remaining READMEs), and E36-03.7 (ensure schema links and illustrative payloads). 
# tayfin-ingestor-jobs

## Overview

CLI-driven ingestion jobs that populate the `tayfin_ingestor` schema. Each job is ephemeral, run-once, and safe to re-run (idempotent upserts).

## Job CLI

Generic pattern:

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs/scripts

# List available targets
./run_<job>.sh list

# Run a specific job
./run_<job>.sh
```

Or directly via Python:

```bash
PYTHONPATH=src python -m tayfin_ingestor_jobs jobs list
PYTHONPATH=src python -m tayfin_ingestor_jobs jobs run <job> <target> --config config/<file>.yml
```

---

## Discovery Job

Resolves index memberships (e.g. Nasdaq-100) and upserts `instruments` + `index_memberships`.

```bash
./scripts/run_discovery.sh
```

Config: `config/discovery.yml`

---

## Fundamentals Job

Computes daily fundamental snapshots per instrument. Provider: Stockdex/Yahoo with yfinance fallback and retries.

```bash
./scripts/run_fundamentals.sh
```

Config: `config/fundamentals.yml`

---

## OHLCV Job

Fetches daily OHLCV candles for all instruments in an index. Currently configured for NDX (Nasdaq-100).

- **Primary provider:** TradingView
- **Fallback provider:** yfinance
- **Target table:** `tayfin_ingestor.ohlcv_daily`
- **Per-ticker logic:** checks the latest existing date and only fetches newer candles

```bash
# Full NDX run
./scripts/run_ohlcv.sh

# Single ticker (debug)
./scripts/run_ohlcv.sh --ticker AAPL

# Custom date window
./scripts/run_ohlcv.sh --from 2025-01-01 --to 2025-06-01

# Limit to first N tickers (testing)
./scripts/run_ohlcv.sh --limit 5
```

Config: `config/ohlcv.yml`

**Optional env vars:**

| Variable | Purpose |
|---|---|
| `TRADINGVIEW_COOKIE` | Authenticated cookie for extended rate limits |
| `OHLCV_RATE_LIMIT_RPS` | Requests per second (default: 2) |
| `OHLCV_RETRY_MAX_ATTEMPTS` | Max retry attempts per ticker (default: 3) |

---

## Configuration

- YAML config files in `config/`.
- Precedence: **CLI flags > env vars > YAML > code defaults**.
- DB credentials are read from the repo-root `.env` file.

## Database

Writes to the `tayfin_ingestor` schema. Migrations managed by Flyway (`tayfin-ingestor/db/migrations/`).

## What this app does NOT do

- No HTTP API (see `tayfin-ingestor-api`).
- No scheduler — jobs are run manually via CLI.
- No authentication.
