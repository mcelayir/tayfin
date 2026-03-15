# Issue 31 — Phase 1 Updated Plan: Scheduler Sequencing

This document contains the task breakdown to implement module-group sequencing in the scheduler (ingestor → indicator → screener). It supplements the epic and is intended for @developer and @lead-dev.

## Goal
Ensure scheduled jobs run in well-defined module-groups and in strict order: all ingestor jobs complete before indicator jobs start; all indicator jobs complete before screener jobs start. Support explicit ordering configuration and cross-instance coordination.

## Constraints & references
- Follow project architecture and bounded-context rules in [docs/architecture/ARCHITECTURE_RULES.md](docs/architecture/ARCHITECTURE_RULES.md).
- Any cross-context database reads must follow the project non-negotiables (use APIs for data); advisory locks within infra are allowed for coordination.
- Update ADRs if this changes runtime semantics.

## Tasks (detailed)

| ID | Task | Description | Files / Targets | Acceptance criteria | Owner | Estimate |
|---:|---|---|---|---|---:|---:|
| 15.1 | Confirm observed race & scope | Re-run smoke test, capture timestamps of job starts; confirm whether multiple scheduler instances exist or single scheduler launches jobs concurrently. | infra/scheduler/scheduler.py logs, `docker compose` logs | Definitive evidence (log excerpt) showing interleaving and source cause | @developer | 0.5d |
| 16.1 | Add explicit `module_order` support | Extend `infra/schedules.yml` schema to accept optional `module_order: ["tayfin_ingestor_jobs","tayfin_indicator_jobs","tayfin_screener_jobs"]`. Keep current `preferred_order` fallback. | infra/schedules.yml (docs/example) and infra/scheduler/scheduler.py parsing | When `module_order` present scheduler uses it; else fallback unchanged | @developer | 0.5d |
| 16.2 | Execute module groups strictly sequentially | Modify `run_once` to iterate module groups in configured order and block on all jobs in a group before proceeding. Ensure `run_command` waits on subprocess completion (already does) and add per-job start/end timestamps to logs. | infra/scheduler/scheduler.py | Logs show group-by-group execution and start/end times; indicator group starts after ingestor complete | @developer | 1.0d |
| 16.3 | Add per-job timeout and backpressure handling | Add a configurable `JOB_TIMEOUT_SECONDS` env var and implement optional per-command timeout handling so a stuck job doesn't block indefinitely. If timeout reached, mark job as failed and proceed to next group (or follow configured fallback). | infra/scheduler/scheduler.py, infra/docker-compose.yml docs | Timeouts are enforced and logged; failure handling policy documented | @developer | 0.5d |
| 17.1 | Implement module-level advisory lock barrier | Before starting a module group, attempt to acquire a DB advisory lock (or a namespaced lock) to prevent two scheduler instances from executing the same group concurrently. Release lock when group completes. Provide configurable lock timeouts. | infra/db_lock.py, infra/scheduler/scheduler.py | Concurrent scheduler instances serialize at module-group level in test harness | @developer | 1.0d |
| 17.2 | Add health checks and idempotency notes | Ensure scheduler healthcheck and idempotent job execution semantics are documented; add guard to skip job if lock not acquired (or retry). | infra/scheduler/*, docs/knowledge/runbooks | Runbook updated; scheduler handles lock loss gracefully | @developer | 0.5d |
| 19.1 | Integration tests: sequencing | Add tests that run `run_once` with mocked long-running jobs (e.g., subprocess that sleeps) to assert ordering. Include test for concurrent scheduler instances asserting serialization via locks. | infra/tests/test_scheduler_sequencing.py | CI tests verify ordering and lock behavior | @developer / QA | 1.0d |
| 20.1 | ADR: scheduling semantics | Draft ADR describing ordering guarantees, lock mechanism, timeout policy, and backward compatibility. | docs/architecture/adr/XXXX-scheduler-sequencing.md | ADR merged into repository | @lead-dev | 0.5d |

## Implementation notes
- Default behavior remains unchanged until `module_order` is specified to avoid surprises.
- Use DB advisory locks already present in `infra/db_lock.py` (scheduler already references `db_lock`) and extend API to support namespaced module locks.
- Keep scheduler logging verbose for smoke-testing: include ISO timestamps for job start/end and module boundaries.

## Quick checklist for PRs
- [ ] Update `infra/schedules.yml` example with `module_order` documented.
- [ ] Small, focused PRs: (A) parsing + ordering logic, (B) advisory lock barrier, (C) timeouts + tests.
- [ ] Update epic (#31) with references to PRs and test results.

---

/cc @developer @lead-dev
