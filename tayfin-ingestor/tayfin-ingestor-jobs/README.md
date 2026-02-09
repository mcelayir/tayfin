# tayfin-ingestor-jobs

Overview
- Runs ingestion jobs that produce data stored in the `tayfin_ingestor` schema.
- Implemented jobs: discovery (index membership) and fundamentals (time-series snapshots).
- US fundamentals are retrieved using Stockdex/Yahoo (with a yfinance fallback and retries).

Implemented jobs
- Discovery job (nasdaq-100): resolves index memberships and upserts `instruments` and `index_memberships`.
- Fundamentals job: computes daily time-series snapshots and writes to `tayfin_ingestor.fundamentals_snapshots`.

Configuration
- YAML config files are located in `tayfin-ingestor/tayfin-ingestor-jobs/config/`.
- Configuration precedence: CLI flags override environment variables, which override YAML values.
- Example `fundamentals.yml` (minimal):

```yaml
kind: index
index_code: nasdaq-100
country: US
provider: stockdex_yahoo
```

How to run locally
- From the repository root (examples):

```
PYTHONPATH=src python -m tayfin_ingestor_jobs jobs list --config tayfin-ingestor/tayfin-ingestor-jobs/config/fundamentals.yml

PYTHONPATH=src python -m tayfin_ingestor_jobs jobs run discovery nasdaq-100 --config tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml

PYTHONPATH=src python -m tayfin_ingestor_jobs jobs run fundamentals nasdaq-100 --config tayfin-ingestor/tayfin-ingestor-jobs/config/fundamentals.yml
```

- The jobs read DB credentials from a repository `.env` (or environment) when present.

Database usage
- Writes to the `tayfin_ingestor` schema (`instruments`, `index_memberships`, `fundamentals_snapshots`).
- Schema migrations are managed with Flyway (see `tayfin-ingestor/db/migrations`).
- `fundamentals_snapshots` is modeled as a time-series table keyed by `(instrument_id, as_of_date, source)`.

Rate limiting
- Provider implementations include retry and backoff logic to mitigate external rate limits (Yahoo). Backoff parameters are configurable via environment variables.

What this app does NOT do
- No HTTP API server (this package contains jobs only).
- No UI.
- No scheduler (jobs are run manually via CLI).
- No authentication.
