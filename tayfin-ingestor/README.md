---
template_version: 1
module: tayfin-ingestor
owner: "@dev"
qa_checklist: true
---

# tayfin-ingestor

## Description
tayfin-ingestor is responsible for ingesting market data (OHLCV, fundamentals, discovery), normalizing it, and persisting raw and derived records for downstream processing (indicator calculations and screener workflows).

## Service Overview
- Responsibility: Data Ingress / Normalization
- Primary interfaces: HTTP API (`tayfin-ingestor-api`), CLI jobs (`tayfin-ingestor-jobs`)
- Owner: @dev

## Getting Started

### Local Commands
| Task | Command | Description |
| :--- | :--- | :--- |
| Start API (dev) | `./tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh` | Start the API service locally |
| Run jobs (example) | `./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh` | Run the OHLCV ingest job locally |
| Run tests | `pytest -q` (in submodule folders) | Run unit tests for API or jobs |

### Environment Variables (top-level)
| Key | Type | Required | Default | Example | Notes |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `DB_URL` | string | Yes | - | `postgres://user:pass@localhost:5432/tayfin` | SQLAlchemy connection string used across submodules |
| `JOB_RUN_ID` | string | Yes | - | `job-20260322-abc123` | Provenance identifier; attach to all persistent writes |

### Execution Examples
- Docker Compose (local dev):
```bash
docker-compose -f infra/docker-compose.yml up --build tayfin-ingestor
```
- Run API (script):
```bash
./tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh
```
- Run job (example):
```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh
```

## Submodules
- API: [tayfin-ingestor/tayfin-ingestor-api/README.md](tayfin-ingestor/tayfin-ingestor-api/README.md) — documents HTTP endpoints and schemas.  
- Jobs: [tayfin-ingestor/tayfin-ingestor-jobs/README.md](tayfin-ingestor/tayfin-ingestor-jobs/README.md) — documents available CLI jobs, cron examples, and providers.

## Observability
- Logs: include `job_run_id` and request IDs in key flows.  
- Metrics: instrument `requests_total`, `ingest_success_total`, `ingest_failure_total` with tags `module`, `endpoint`.

## Security
- Do not commit secrets; use environment variables and placeholders in examples.

## QA Checklist
- [ ] API curl examples in `tayfin-ingestor-api` run successfully against local dev.  
- [ ] Job scripts in `tayfin-ingestor-jobs` execute and produce expected outputs.  
- [ ] Environment variables documented and validated.

## Links
- API code: `tayfin-ingestor/tayfin-ingestor-api/src`  
- Jobs code: `tayfin-ingestor/tayfin-ingestor-jobs/src`  
- Artifacts list: `tayfin-ingestor/artifacts.md`

## CHANGELOG
- 2026-03-22 — Initial README created (@dev)

---

Note: This top-level README intentionally links to submodule READMEs for endpoint and job details. Fill submodule READMEs next (E36-03.3, E36-03.4) with concrete schemas and examples.
# tayfin-ingestor

Bounded context responsible for **discovering instruments**, ingesting **fundamentals** and **OHLCV** data, and exposing read-only APIs over that data.

## Apps

| App | Purpose |
|---|---|
| `tayfin-ingestor-jobs` | CLI-driven ingestion jobs (discovery, fundamentals, OHLCV) |
| `tayfin-ingestor-api` | Read-only Flask API serving ingested data |

---

## Available Jobs

### Discovery

Resolves index memberships (e.g. Nasdaq-100) and upserts `instruments` + `index_memberships`.

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs/scripts
./run_discovery.sh
```

### Fundamentals

Fetches daily fundamental snapshots per instrument. Primary provider: Stockdex/Yahoo with yfinance fallback.

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs/scripts
./run_fundamentals.sh
```

### OHLCV

Fetches daily OHLCV candles per instrument. Primary provider: **TradingView**, fallback: **yfinance**. Writes to `tayfin_ingestor.ohlcv_daily`.

```bash
# Full NDX run
cd tayfin-ingestor/tayfin-ingestor-jobs/scripts
./run_ohlcv.sh

# Single ticker
./run_ohlcv.sh --ticker AAPL

# Custom date range
./run_ohlcv.sh --from 2025-01-01 --to 2025-06-01

# Limit to first N tickers (testing)
./run_ohlcv.sh --limit 5
```

**Optional env vars:**

- `TRADINGVIEW_COOKIE` — authenticated cookie for TradingView (extends rate limits)
- `OHLCV_RATE_LIMIT_RPS`, `OHLCV_RETRY_MAX_ATTEMPTS` — tune retry/rate-limit behaviour

---

## Database Tables

All tables live in the `tayfin_ingestor` schema. Migrations are managed with Flyway (`db/migrations/`).

| Table | Description |
|---|---|
| `job_runs` / `job_run_items` | Audit trail for every job execution |
| `instruments` | Discovered tickers, unique on `(ticker, country)` |
| `index_memberships` | Maps index codes (e.g. NDX) to instruments |
| `fundamentals_snapshots` | Daily fundamental metrics, keyed by `(instrument_id, as_of_date, source)` |
| `ohlcv_daily` | Daily OHLCV candles — one row per instrument per date, unique on `(instrument_id, as_of_date)` |

---

## Quick Validation SQL

### Last candles for a ticker

```sql
SELECT as_of_date, open, high, low, close, volume, source
FROM tayfin_ingestor.ohlcv_daily od
JOIN tayfin_ingestor.instruments i ON i.id = od.instrument_id
WHERE i.ticker = 'AAPL'
ORDER BY as_of_date DESC
LIMIT 10;
```

### Detect bad rows

```sql
SELECT COUNT(*)
FROM tayfin_ingestor.ohlcv_daily
WHERE close <= 0 OR high < low;
```

### Count candles per ticker

```sql
SELECT i.ticker, COUNT(*) AS candle_count, MIN(od.as_of_date) AS first, MAX(od.as_of_date) AS last
FROM tayfin_ingestor.ohlcv_daily od
JOIN tayfin_ingestor.instruments i ON i.id = od.instrument_id
GROUP BY i.ticker
ORDER BY candle_count DESC;
```
