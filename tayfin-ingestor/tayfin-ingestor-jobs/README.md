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
