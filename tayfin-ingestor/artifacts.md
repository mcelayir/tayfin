# Artifacts for `tayfin-ingestor`

This file lists repo-relative paths to code, API handlers, job scripts, config, migrations, and example artifacts useful for documenting `tayfin-ingestor` READMEs (E36-03.1).

## API (handlers, app, serializers, repos)
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/app.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/serializers/ohlcv_serializer.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/serializers/__init__.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/ohlcv_repository.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/fundamentals_repository.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/instrument_repository.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/index_membership_repository.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/config/loader.py
- tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/db/engine.py

## Jobs (CLI entrypoints, job modules, providers)
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/cli/main.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/__main__.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/ohlcv_job.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/ohlcv_backfill_job.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/fundamentals_job.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/discovery_job.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/service.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/normalize.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/tradingview_provider.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/yfinance_provider.py
- tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/fundamentals/providers/stockdex_provider.py

## Scripts & run helpers
- tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh
- tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv.sh
- tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_ohlcv_backfill.sh
- tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_fundamentals.sh
- tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_discovery.sh

## Config files
- tayfin-ingestor/tayfin-ingestor-api/config/ingestor.yml
- tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml
- tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv_backfill.yml
- tayfin-ingestor/tayfin-ingestor-jobs/config/fundamentals.yml
- tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml

## Migrations / DB
- tayfin-ingestor/db/migrations/V1__init_audit.sql
- tayfin-ingestor/db/migrations/V2__create_discovery_tables.sql
- tayfin-ingestor/db/migrations/V3__create_fundamentals_snapshots.sql
- tayfin-ingestor/db/migrations/V4__add_exchange_to_instruments.sql
- tayfin-ingestor/db/migrations/V5__create_ohlcv_daily.sql
- tayfin-ingestor/db/migrations/README.md

## Tests
- tayfin-ingestor/tayfin-ingestor-api/tests/test_ohlcv_api.py
- tayfin-ingestor/tayfin-ingestor-api/tests/test_fundamentals_api.py
- tayfin-ingestor/tayfin-ingestor-api/tests/test_config_engine.py
- tayfin-ingestor/tayfin-ingestor-jobs/tests/test_ohlcv_backfill_failure_paths.py
- tayfin-ingestor/tayfin-ingestor-jobs/tests/test_discovery_network_failure.py
- tayfin-ingestor/tayfin-ingestor-jobs/tests/test_adr06_credentials.py

## Existing READMEs
- tayfin-ingestor/README.md
- tayfin-ingestor/tayfin-ingestor-api/README.md
- tayfin-ingestor/tayfin-ingestor-jobs/README.md

## Notes / Suggested next actions
- Inspect `app.py` to identify API routes and parameters to document.  
- Use serializer files (`serializers/`) as authoritative request/response shapes or link to repository code.  
- Use job `jobs/*.py` files as authoritative job names and parameters; add sample CLI invocations from `cli/main.py` and scripts.  
- If JSON Schema files are needed, consider deriving them from serializers or adding `schemas/` under the API module.  
