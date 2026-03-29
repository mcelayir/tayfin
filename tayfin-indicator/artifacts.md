<!--
Artifact inventory for E36-04.1 — collected sources and authoritative locations
Generated: 2026-03-22
Owner: @dev
-->
# tayfin-indicator — Artifacts & authoritative references

Summary: the following repo-relative paths are the primary sources, entry points, jobs, configs, migrations, and tests relevant to the `tayfin-indicator` module. Use these as the starting point when drafting READMEs and extracting canonical input/output shapes.

- Module top-level
  - tayfin-indicator/README.md — existing top-level README (review and align to canonical template)

- API
  - tayfin-indicator/tayfin-indicator-api/README.md — API README (review for endpoints/examples)
  - tayfin-indicator/tayfin-indicator-api/src/tayfin_indicator_api/app.py — API handlers / route defs
  - tayfin-indicator/tayfin-indicator-api/src/tayfin_indicator_api/serializers/ — response serializers (look for canonical shapes)
  - tayfin-indicator/tayfin-indicator-api/src/tayfin_indicator_api/repositories/indicator_repository.py — DB read models for indicators
  - tayfin-indicator/tayfin-indicator-api/config/indicator.yml — API config for indicator endpoints
  - tayfin-indicator/tayfin-indicator-api/scripts/run_api.sh — helper script to run API locally

- Jobs
  - tayfin-indicator/tayfin-indicator-jobs/README.md — jobs README (review)
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/indicator/compute.py — indicator compute helpers
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/jobs/ma_compute_job.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/jobs/atr_compute_job.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/jobs/vol_sma_compute_job.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/jobs/rolling_high_compute_job.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/jobs/registry.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/cli/main.py — Typer CLI entry for jobs
  - tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml — jobs config
  - tayfin-indicator/tayfin-indicator-jobs/requirements.txt

- DB & migrations
  - tayfin-indicator/db/migrations/V1__create_schema.sql
  - tayfin-indicator/db/migrations/V2__create_job_runs.sql
  - tayfin-indicator/db/migrations/V3__create_job_run_items.sql
  - tayfin-indicator/db/migrations/V4__create_indicator_series.sql — indicator series table

- Repositories & persistence
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/repositories/indicator_series_repository.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/repositories/job_run_repository.py
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/repositories/job_run_item_repository.py

- Clients / integration
  - tayfin-indicator/tayfin-indicator-jobs/src/tayfin_indicator_jobs/clients/ingestor_client.py — ingestor integration
  - tayfin-indicator/tayfin-indicator-api/src/tayfin_indicator_api/clients/ingestor_client.py

- Tests
  - tayfin-indicator/tayfin-indicator-jobs/tests/test_compute.py
  - tayfin-indicator/tayfin-indicator-jobs/tests/test_job_orchestration.py
  - tayfin-indicator/tayfin-indicator-api/tests/test_api_endpoints.py
  - tayfin-indicator/tayfin-indicator-api/tests/test_config_engine.py

- Infrastructure / Docker
  - tayfin-indicator/tayfin-indicator-api/Dockerfile
  - tayfin-indicator/tayfin-indicator-jobs/Dockerfile

- Misc
  - tayfin-indicator/tayfin-indicator-jobs/scripts/.gitkeep
  - tayfin-indicator/tayfin-indicator-jobs/requirements-dev.txt

Notes and next steps for E36-04.1:
- Extract canonical input/output shapes from `serializers` and job `compute.py` functions.  
- Use `indicator_series` DB migration (V4) to identify persisted column types.  
- Gather small example payloads for API responses (build minimal JSON examples).  
- Identify env vars referenced in `config/indicator.yml` and job CLI to populate env tables (E36-04.5).
