# Infra Runbook — Scheduler & Local Compose

Purpose
- Operational notes for running and troubleshooting the local infra scheduler and Compose-based developer environment.

Quick Start
- Start the main infra stack (DB, migrations, APIs, scheduler once):
  - `docker compose -f infra/docker-compose.yml up --build --remove-orphans`
  - With an env file: `docker compose --env-file .env -f infra/docker-compose.yml up --build --remove-orphans`
- Run only the scheduler (with current repo image):
  - `docker compose -f infra/docker-compose.yml up --build scheduler`
  - With an env file: `docker compose --env-file .env -f infra/docker-compose.yml up --build scheduler`

Database migrations
- Flyway runs as a Compose service using `infra/flyway-run.sh`. It applies migrations located under each service's `db/migrations` folder. If migrations fail, inspect the `flyway` container logs:
  - `docker compose -f infra/docker-compose.yml logs --follow flyway`
  - With an env file: `docker compose --env-file .env -f infra/docker-compose.yml logs --follow flyway`

Scheduler behaviour
- Location: `infra/scheduler/`
- Entrypoint: image built from `infra/scheduler/Dockerfile` launched by the `scheduler` service in Compose.
- Default mode: the Compose `scheduler` service runs with `--once` (run all schedules once and exit). To run continuously remove `--once`.
- Ordering: the scheduler enforces module-group sequencing in this order: `tayfin_ingestor_jobs` → `tayfin_indicator_jobs` → `tayfin_screener_jobs` → others.
- Discovery-first: within `tayfin_ingestor_jobs`, discovery jobs run before other ingestor schedules to ensure instruments exist.
- Locks: the scheduler uses Postgres advisory locks at two levels:
  - Module-level lock (`module:<module_name>`) serializes execution of a module group across scheduler instances.
  - Per-schedule job-level locks prevent duplicate concurrent runs of the same schedule.
  - Lock helpers are implemented in `infra/scheduler/db_lock.py`.

Important env vars (Compose)
- `POSTGRES_HOST` — database host (Compose uses `db`).
- `SCHEDULER_ENABLED` — toggle for scheduler behavior in dev images (default `0` in Compose).
- `SCHEDULER_DB_CONNECT_ATTEMPTS` & `SCHEDULER_DB_CONNECT_WAIT` — connection retry settings used by the scheduler.
- `PYTHONPATH` — Compose mounts project source for scheduler image; adjust if adding new job packages.

Operational recipes
- Run a single scheduled job locally (example):
  - `docker compose -f infra/docker-compose.yml run --rm scheduler python -m tayfin_ingestor_jobs jobs run discovery nasdaq-100 --config /app/config/discovery.yml`
  - With an env file: `docker compose --env-file .env -f infra/docker-compose.yml run --rm scheduler python -m tayfin_ingestor_jobs jobs run discovery nasdaq-100 --config /app/config/discovery.yml`
- Reproduce the race that previously caused screener failures:
  - Start compose with scheduler `--once` and inspect logs; if screener failures appear with "No OHLCV data", confirm ingestor discovery/ohlcv completed before screener started.

Troubleshooting
- "No instruments found / No OHLCV data": ensure ingestor discovery and OHLCV jobs ran and succeeded before screeners. The scheduler now sequences ingestor first; if manual debugging, run discovery first.
- Missing config files in container: confirm repository `config` files are mounted/copied into `/app/config` in image build and `infra/schedules.yml` uses explicit `--config /app/config/...` paths.
- Advisory lock starvation: module-level locks use retries; increase `SCHEDULER_DB_CONNECT_ATTEMPTS` / wait settings in Compose if necessary.

Testing
- Infra smoke test: `pytest infra/tests/test_smoke_jobs.py` (requires Python dev env and dependencies). In CI, ensure smoke tests are executed in an environment with DB and Flyway applied.

Related docs & code
- ADR: [ADR 07: Infra Scheduler App — Placement, Design and Operational Semantics](docs/architecture/adr/ADR_07_INFRA_SCHEDULER_APP.md)
- Scheduler code: infra/scheduler/scheduler.py
- Lock helper: infra/scheduler/db_lock.py
- Schedules: infra/schedules.yml
