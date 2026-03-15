# ADR 07: Infra Scheduler App — Placement, Design and Operational Semantics

Status: Proposed

Context
- The repository contains a minimal scheduler prototype implemented under `infra/scheduler/` used by local Compose-based environments. The scheduler runs jobs defined in `infra/schedules.yml`, invokes Typer-based job CLIs (e.g. `python -m tayfin_ingestor_jobs ...`), and coordinates execution ordering.

Decision
- Place the scheduler under the `infra/` folder as an infrastructure component rather than a first-class domain package (e.g. `tayfin-scheduler`). The scheduler will:
  - Be a minimal, operational helper intended for local development and simple on-host scheduling. It is NOT intended as a productized service; production-grade orchestration remains out-of-scope for this ADR.
  - Provide deterministic execution ordering (module-group sequencing: ingestor → indicator → screener) and basic coordination via Postgres advisory locks (`infra/scheduler/db_lock.py`).

Rationale
- Why under `infra/` rather than a separate `tayfin-scheduler` package:
  - Operational intent: the scheduler is an infra tool to wire up existing job packages (ingestor/indicator/screener) for local/staging smoke tests and developer workflows.
  - Reduced API surface: scheduling is not a runtime public service for other contexts to depend on; it orchestrates existing Typer CLIs and relies on the repository structure and packaged job CLIs.
  - Deployment model: running in Compose with the rest of infra (db, APIs) simplifies dev experience and reduces cross-repo deployment concerns.

How it works (implementation notes)
- `infra/scheduler/scheduler.py`
  - Loads `infra/schedules.yml` (prefers `/app/schedules.yml` when running inside container).
  - Groups scheduled entries by Python module token extracted from `-m <module>` in the command string.
  - Executes module groups in preferred order: `tayfin_ingestor_jobs`, `tayfin_indicator_jobs`, `tayfin_screener_jobs`, then any other modules.
  - Executes jobs sequentially within each module group and captures subprocess stdout/stderr for visibility.
  - Employs two levels of advisory locks (via `db_lock`):
    - Module-level lock `module:<mod>` to serialize access to the module group across scheduler instances.
    - Job-level lock keyed by schedule name to avoid duplicate concurrent runs of the same schedule.

- `infra/scheduler/db_lock.py`
  - Small helper using a psycopg connection and `pg_try_advisory_lock` / `pg_advisory_unlock` to implement locks keyed by stable 32-bit integers derived from names.

- `infra/scheduler/run_job.sh` (operational wrapper)
  - Optional script used in container images to provide a repeatable entrypoint which calls the Python CLI with proper env and config paths. (If present in the repo, maintainers should keep it lightweight.)

Alternatives considered
- Implement scheduler as a separate packaged service `tayfin-scheduler` with its own API and releases.
  - Pros: clearer owner boundary, can be treated as a product with API-driven scheduling, versioned deploys.
  - Cons: increased maintenance, cross-team coordination, not necessary for local Compose smoke-run experience.

Consequences
- Short-term: fast developer feedback loop and simple Compose-based smoke testing of job flows.
- Operational: scheduler semantics (module sequencing, advisory locks) will be considered part of infra contract; changes should be documented in ADR and runbooks.
- Risks: infra scheduler is not a full scheduler product; do not rely on it for high-availability production scheduling. For production, use dedicated orchestrators (Airflow/Kubernetes CronJobs/etc.).

Migration & Rollout
- The change introducing sequencing and module locks is backward compatible for dev Compose runs. Rollout consists of updating the scheduler image (if used) and merging the ADR + runbook.

Tests & Acceptance
- Add infra smoke tests that validate ordering and module-level locking behavior (already present in `infra/tests/test_smoke_jobs.py`).

Related
- Code: `infra/scheduler/scheduler.py`, `infra/scheduler/db_lock.py`
- Runbook: `docs/ops/infra-runbook.md`
