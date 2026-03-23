<!--
Local verification report for E36-04.8
Generated: 2026-03-23
Owner: @dev
-->
# E36-04.8 — Local Verification & QA Readiness

Summary
- Purpose: validate README example payloads against the module JSON Schemas and run a safe CLI check (`jobs list`).  
- Environment: local dev machine; Python 3.12 in repo `.venv` (activated). `jsonschema` is available in the environment.

Commands executed
1. Validate README examples against schemas

```bash
python3 tayfin-indicator/tayfin-indicator-api/scripts/validate_examples.py
```

2. List configured jobs (safe CLI check)

```bash
PYTHONPATH=tayfin-indicator/tayfin-indicator-jobs/src python3 -m tayfin_indicator_jobs jobs list --config tayfin-indicator/tayfin-indicator-jobs/config/indicator.yml
```

Validation results

Output from `validate_examples.py` (JSON):

{
  "validations": [
    {"schema": "indicator_latest", "ok": true, "message": "OK"},
    {"schema": "indicator_range", "ok": true, "message": "OK"},
    {"schema": "indicator_index_latest", "ok": true, "message": "OK"},
    {"schema": "indicator_series", "ok": true, "message": "OK"}
  ]
}

All README examples validated successfully against their corresponding JSON Schemas.

CLI check

Output from `jobs list` (printed to stdout):

job: ma_compute
  - nasdaq-100: index_code=NDX indicators=[sma({'window': 50}), sma({'window': 150}), sma({'window': 200})]
job: atr_compute
  - nasdaq-100: index_code=NDX indicators=[atr({'window': 20})]
job: vol_sma_compute
  - nasdaq-100: index_code=NDX indicators=[vol_sma({'window': 50})]
job: rolling_high_compute
  - nasdaq-100: index_code=NDX indicators=[rolling_high({'window': 252})]

Notes / Blockers
- I validated README examples against schemas locally — success.  
- The `jobs list` CLI runs when `PYTHONPATH` points at `tayfin-indicator-jobs/src` and prints configured jobs; this requires no DB and is safe.  
- I did not run a full job run (`jobs run ...`) because that requires a reachable Postgres instance and migrations applied. Attempting to run a compute job without DB would fail; to execute full job verification, the following environment is required:
  - A running Postgres instance with migrations applied for `tayfin_indicator` schema (see `db/migrations/`).
  - `POSTGRES_*` env vars set to point to the DB.  
  - (Optional) an ingestor API reachable at `TAYFIN_INGESTOR_API_BASE_URL` or a mocked `IngestorClient`.

Recommended next steps for full QA
1. Spin up a local Postgres instance (docker-compose or test DB), apply migrations under `tayfin-indicator/db/migrations/`.  
2. Run a single job for a sample ticker with `--ticker` and verify `indicator_series` rows are written with `created_by_job_run_id` set.  
3. Re-run `validate_examples.py` if examples change.

Artifacts produced
- Validator script: `tayfin-indicator/tayfin-indicator-api/scripts/validate_examples.py` (committed).  
- This report: `.github/issues/36/e36-04-task-local-verification-report.md` (committed).  
