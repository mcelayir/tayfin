Posting Phase 1 & 2 subtasks for @developer below.

**My name is GitHub Copilot.**

---

Phase 1 — Packaging & Config: actionable subtasks for @developer

| ID | Subtask | Description | Files / Targets | Acceptance criteria | Estimate | Assignee |
|---:|---|---|---|---|---:|---|
| 1.1 | Add explicit `--config` support to scheduler commands | Update `infra/schedules.yml` entries to pass explicit config paths for each job so runtime does not rely on packaged defaults | `infra/schedules.yml` | Scheduler `--once` runs jobs and CLI loads given config (no "Job '...' not found") | 1h | @developer (infra) |
| 1.2 | Add environment-aware `load_config` fallback | Make `tayfin_*_jobs.config.loader.load_config` check well-known FS locations (e.g. `/app/config/<file>`) before package relative path; keep existing behavior | `tayfin-*/src/*/config/loader.py` (screener/ingestor) | CLI loads config when `--config` not provided if config exists at `/app/config` | 2h | @developer (packaging) |
| 1.3 | Ensure config files are included in Docker images or mounted | Update Dockerfiles / image build COPY or image entrypoint docs to include `/app/config/*.yml` or document mount volumes | Dockerfiles under each `*-jobs` and infra README | Built staging images contain `/app/config/*.yml` or `docker-compose` mounts are documented | 2h | @developer (packaging) |
| 1.4 | Update scheduler run environment variables & timeouts | Add recommended env vars (e.g., `TAYFIN_INGESTOR_API_BASE_URL`, `SCHEDULER_DB_CONNECT_*`) and sensible command timeouts in compose/scheduler runtime | `infra/scheduler/*`, `docker-compose` or infra config | Scheduler runs use provided envs; DB connect/retry settings present | 1h | @developer (infra) |
| 1.5 | Smoke-run `scheduler --once` in dev with updated config | Execute locally with `PYTHONPATH` or container to verify the change | local run or container | Jobs now print CLI outputs showing config loaded and proceed to job-run (or fail with clear messages) | 1h | @developer (infra) |


Phase 2 — Job resilience & correctness: actionable subtasks for @developer

| ID | Subtask | Description | Files / Targets | Acceptance criteria | Estimate | Assignee |
|---:|---|---|---|---|---:|---|
| 2.1 | Make `ohlcv_backfill` handle empty instrument sets gracefully | Change `_resolve_instruments` / `OhlcvBackfillJob` to return structured exit (no exception crash) and clear message: “No instruments found — run discovery” | `tayfin-ingestor/tayfin-ingestor-jobs/src/.../ohlcv_backfill_job.py`, `ohlcv/service.py` | Backfill CLI exits with code 1 and explicit message; scheduler stderr shows the message (not opaque traceback) | 2h | @developer (ingestor) |
| 2.2 | Standardize exit codes & messages for missing-config/data | Ensure CLI uses consistent exit codes and machine-friendly messages for: missing config, missing target, missing instruments, provider failures | `*/cli/main.py` across jobs | Scheduler can reliably detect failure reason from proc.stderr; tests assert messages | 2h | @developer (screener/ingestor) |
| 2.3 | Add/extend retries + exponential backoff for provider calls | Ensure `TradingView`/`yfinance` calls use `retry_with_backoff`; increase/log retries for transient errors and surface fallback usage | `ingestor/ohlcv/providers/*`, `ohlcv/service.py` | Transient provider errors retried; logs show fallback to yfinance on TV failure | 3h | @developer (ingestor) |
| 2.4 | Ensure idempotent upserts & job_run provenance | Verify `ohlcv_repo.upsert_bulk` and screener repositories attach `job_run_id` and are idempotent; add small guard if missing | `*/repositories/*_repository.py` | Upserts are idempotent; job rows contain `created_by_job_run_id`/audit fields | 2h | @developer (screener/ingestor) |
| 2.5 | Add clearer job-run item reporting for partial success | When some chunks succeed and some fail, include chunk-level errors in `job_run_item` and CLI summary | `ohlcv/service.py`, `ohlcv_backfill_job.py` | CLI summary shows per-ticker chunks_attempted/succeeded and chunk_errors; tests assert structure | 3h | @developer (ingestor) |
| 2.6 | Add integration test harness (mocked providers & DB) | Create a lightweight test that runs `jobs run ohlcv_backfill` with mocked `InstrumentQueryRepository` and providers to assert behavior on empty instruments and provider fallback | `*/tests/test_ohlcv_backfill_integration.py` | Tests run locally/CI and cover empty-instruments and fallback paths | 4h | @developer (qa) |


Notes for @developer
- Follow code style and SQLAlchemy Core rules (see `docs/architecture/CODEBASE_CONVENTIONS.md` and `docs/architecture/TECH_STACK_RULES.md`). Any cross-context DB reads must use HTTP API (no direct DB access across bounded contexts).
- If any subtask changes the job contract (CLI args, config shape, or audit fields), create an ADR under `docs/architecture/adr/` and attach it to the PR.
- Small, incremental PRs preferred: (A) infra-only `infra/schedules.yml` change, (B) `load_config` fallback + tests, (C) ingestor resiliency changes + tests.
- Coordinate with packaging/ops to confirm where configs will live in images; prefer infra-first (explicit `--config` + mounts) to reduce risk.

/cc @developer
