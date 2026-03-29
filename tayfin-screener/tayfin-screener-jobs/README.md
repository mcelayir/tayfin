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
- `TAYFIN_CONFIG_DIR` — directory holding job target configs.
- `JOB_RUN_ID` — optional: if set, jobs should use this `job_run_id` rather than creating a new one (useful for manual runs and end-to-end testing).

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
