# tayfin-screener-jobs

Overview
--------
This package contains scheduled and ad-hoc jobs that compute and persist screener results (VCP, MCSA, and other strategies). Jobs follow the repository's Typer-based CLI conventions and must attach a `job_run_id` to all writes for provenance.

Location
--------
- Source: `tayfin-screener/tayfin-screener-jobs/src`
- Config: `tayfin-screener/tayfin-screener-jobs/config`
- Migrations: `tayfin-screener/db/migrations`

Running jobs
------------
Jobs are executed via the project's Typer CLI. Example (from repo root):

```bash
python -m tayfin_screener_jobs.main run <job-name> --target <target-name>
```

Example: run a nightly screener compute for a target configuration:

```bash
export TAYFIN_CONFIG_DIR=./tayfin-screener/tayfin-screener-jobs/config
python -m tayfin_screener_jobs.main run screener_compute --target nasdaq-100
```

Provenance
----------
- All job writes must include `created_by_job_run_id` (UUID) and `created_at` timestamps.
- Jobs should call the shared job-run helper to create a `job_run` record before performing writes.

Env vars
--------
- `DATABASE_URL` — Postgres connection for writes and migrations.
	- Example: `postgresql://tayfin:password@localhost:5432/tayfin_dev`
- `TAYFIN_CONFIG_DIR` — directory holding job target configs.
	- Example: `./tayfin-screener/tayfin-screener-jobs/config`
- `JOB_RUN_ID` — optional: if set, jobs should use this `job_run_id` rather than creating a new one (useful for manual runs and end-to-end testing).
	- Example: `2f1e6b10-3c4a-4d2a-9f5b-3a8b9d6c7e1f`
- `TAYFIN_HTTP_TIMEOUT_SECONDS` — HTTP client timeout used when calling other services. Example: `10`

Example run (local)
-------------------
```bash
export DATABASE_URL=postgresql://tayfin:password@localhost:5432/tayfin_dev
export TAYFIN_CONFIG_DIR=./tayfin-screener/tayfin-screener-jobs/config
# optional: reuse a job_run id created by a test harness
export JOB_RUN_ID=2f1e6b10-3c4a-4d2a-9f5b-3a8b9d6c7e1f
python -m tayfin_screener_jobs.main run screener_compute --target nasdaq-100
```

Notes
-----
- Use `JOB_RUN_ID` for manual or CI-driven invocations when you want to correlate writes across multiple steps.
- Do not commit secrets into repo files; use env-based secrets or the CI secrets store.

Testing & Validation
--------------------
- Unit tests live under `tayfin-screener/tayfin-screener-jobs/tests`.
- For README example validation, provide JSON Schema files for persisted rows under `tayfin-screener/tayfin-screener-api/schemas/` and run the repo validator.

Notes for reviewers
-------------------
- Ensure job examples are runnable and do not assume production-only resources.
- Keep example configs minimal and include `target` names used in the repo's CI (if any).

Next steps
----------
1. Add example target config files to `config/` used in the README examples.
2. Extract persisted-row schema and example JSON for validator (E36-05.7).
Purpose: Screening jobs for candidate selection.
Phase: Phase 1 skeleton (no business logic yet).
Context: tayfin-screener
