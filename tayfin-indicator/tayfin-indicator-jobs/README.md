# tayfin-indicator-jobs

Scheduled / CLI jobs that compute technical indicators and persist results.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m tayfin_indicator_jobs --help
```

## Jobs Overview

This package contains Typer-based jobs that compute indicator series from OHLCV data and persist rows into the `indicator_series` table. Primary jobs include:

- `ma_compute` — compute moving averages (SMA) for configured windows.  
- `atr_compute` — compute Average True Range (ATR).  
- `vol_sma_compute` — compute volume-smoothed SMA.  
- `rolling_high_compute` — compute rolling highs over a window.

Jobs are configured via `config/indicator.yml` and invoked through the CLI (see examples below).

## Example CLI Usage

List configured jobs and targets:
```bash
python -m tayfin_indicator_jobs jobs list --config config/indicator.yml
```

Run a job for a configured target (example: MA compute for nasdaq-100):
```bash
python -m tayfin_indicator_jobs jobs run ma_compute nasdaq-100 --config config/indicator.yml
```

Run single-ticker override and limit:
```bash
python -m tayfin_indicator_jobs jobs run atr_compute nasdaq-100 --config config/indicator.yml --ticker AAPL --limit 1
```

## Provenance (`JOB_RUN_ID`)

All jobs create and propagate a `job_run_id` for provenance. When the job writes indicator values the repository functions set `created_by_job_run_id` (and `updated_by_job_run_id` on upserts) as defined in `db/migrations/V4__create_indicator_series.sql`.

Example logging from a job run (printed to stdout):
```
[atr_compute] job_run_id  = job-20260323-abc123
```

When documenting job examples or reproducing runs, capture the `job_run_id` and include it when querying `job_run` and `job_run_items` tables for debugging and audit.

## Environment Variables

Jobs use the same DB configuration as the API. Key variables:

| Key | Type | Required | Default | Example | Notes |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `POSTGRES_HOST` | string | Yes | `localhost` | `localhost` | Database host |
| `POSTGRES_PORT` | integer | Yes | `5432` | `5432` | Database port |
| `POSTGRES_DB` | string | Yes | `tayfin` | `tayfin` | Database name |
| `POSTGRES_USER` | string | Yes | `tayfin_user` | `tayfin_user` | Database user |
| `POSTGRES_PASSWORD` | string | Conditionally | _(empty)_ | `REDACTED` | Database password (do not commit) |
| `TAYFIN_INGESTOR_API_BASE_URL` | string | Conditionally | `http://localhost:8000` | `http://localhost:8000` | Used by `IngestorClient` to fetch OHLCV / index members |
| `TAYFIN_HTTP_TIMEOUT_SECONDS` | integer | No | `20` | `20` | Default timeout for HTTP calls made by clients (jobs pick this up if present) |
| `TAYFIN_CONFIG_DIR` | string | No | - | `/app/config` | Optional path to override package `config/` with runtime YAML |
| `TAYFIN_INDICATOR_LOOKBACK_DAYS` | integer | No | `420` | `420` | Lookback window in days used by jobs when computing indicators (can be overridden per job via CLI)

## Where values are persisted

Indicator rows are persisted into the schema/table created by: `db/migrations/V4__create_indicator_series.sql`. Repositories responsible for writes live in `src/tayfin_indicator_jobs/repositories/indicator_series_repository.py`.

## QA Checklist

- [ ] Running a single job with `--ticker` writes expected rows to `indicator_series` with `created_by_job_run_id` set.  
- [ ] Job logs include printed `job_run_id` for traceability.  
- [ ] `config/indicator.yml` targets are runnable via CLI examples above.

## Troubleshooting

- If jobs fail to connect to DB, verify `POSTGRES_*` env vars and that migrations have been applied.  
- If ingestor calls fail, confirm `TAYFIN_INGESTOR_API_BASE_URL` and that the ingestor API is running.

