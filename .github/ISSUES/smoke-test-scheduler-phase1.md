# Smoke Test Plan — Scheduler Phase 1

DO NOT COMMIT THIS FILE — local runbook for manual smoke testing of PR #32 (branch: feat/epic/scheduler-config-packaging).

## Purpose
Quick validated runbook to smoke-test the scheduler and scheduled jobs after Phase 1 changes (explicit `--config` in `infra/schedules.yml`, loader fallbacks, configs copied into images).

## Acceptance criteria
- AC-1: Scheduler prints module group execution lines for `tayfin_ingestor_jobs` and `tayfin_screener_jobs`.
- AC-2: Scheduler prints `[scheduler] executing: <full command>` for each scheduled job and shows the subprocess stdout/stderr.
- AC-3: Jobs load config successfully (no `Job '...' not found in config.`). If data missing, errors are explicit (e.g., `No instruments found — run discovery`).
- AC-4: Scheduler process itself does not crash with uncaught tracebacks. Any job failures appear as `[scheduler] failures: [...]` at the end.

## Summary of approach
1. Checkout the feature branch locally.
2. Build and run the minimal Compose stack with the `scheduler` service (it runs `--once`).
3. Stream the scheduler logs and inspect outputs against acceptance criteria.
4. Optionally inspect generated reports and DB job_run rows.

## Steps & Commands
Run these from the repository root.

### Step 1 — Prepare checkout & env
```bash
git fetch origin
git checkout feat/epic/scheduler-config-packaging
git pull --ff-only origin feat/epic/scheduler-config-packaging

cp .env.example .env || true
# Edit .env if you need to change POSTGRES credentials or other vars
```

### Step 2 — Build and start scheduler (single-run)
Build and run scheduler (foreground):
```bash
docker compose -f infra/docker-compose.yml --env-file .env up --build --remove-orphans scheduler
```

Optional: run detached (build and start dependent services) then inspect logs:
```bash
docker compose -f infra/docker-compose.yml --env-file .env up --build -d db flyway ingestor-api indicator-api screener-api scheduler
```

### Step 3 — Stream scheduler logs
```bash
docker compose -f infra/docker-compose.yml --env-file .env logs -f scheduler
```

Look for these lines in the logs:
- `[scheduler] executing module group: tayfin_ingestor_jobs (N jobs)`
- `[scheduler] executing module group: tayfin_screener_jobs (N jobs)`
- `[scheduler] executing: python -m tayfin_ingestor_jobs jobs run ohlcv_backfill nasdaq-100 --config /app/config/ohlcv_backfill.yml` (and similar commands)
- CLI outputs from each job (listings, summaries, or explicit error messages)
- Final: either no failures or `[scheduler] failures: [...]` list

### Step 4 — Inspect job outputs / reports (if produced)
If backfill reports are generated, scheduler/job logs will print a path like `/app/out/backfill/ohlcv_backfill_<target>_<ts>.json`.
To list reports inside scheduler container:
```bash
docker compose -f infra/docker-compose.yml --env-file .env exec scheduler bash -lc "ls -la /app/out/backfill || true"
```
To copy report(s) to host:
```bash
CONTAINER=$(docker compose -f infra/docker-compose.yml --env-file .env ps -q scheduler)
mkdir -p ./tmp/backfill-reports
docker cp ${CONTAINER}:/app/out/backfill/ ./tmp/backfill-reports/ || true
```

### Step 5 — Inspect DB job_runs (optional)
```bash
docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT id, job_name, status, created_at FROM job_runs ORDER BY created_at DESC LIMIT 10;"
```

### Step 6 — Collect logs for triage
If failures occur, save the scheduler logs to a file to attach to the epic:
```bash
docker compose -f infra/docker-compose.yml --env-file .env logs scheduler > scheduler-logs.txt
```
Also collect any backfill JSON reports and job-specific stderr/stdout snippets.

## Troubleshooting checks
- Verify `/app/config` exists inside the scheduler container and contains expected YAML files:
```bash
docker compose -f infra/docker-compose.yml --env-file .env exec scheduler bash -lc "ls -la /app/config || true"
```
- Verify scheduler sees the expected `infra/schedules.yml` (container path `/app/schedules.yml`):
```bash
docker compose -f infra/docker-compose.yml --env-file .env exec scheduler bash -lc "cat /app/schedules.yml || true"
```
- If you see `schedule <name> has no cmd, skipping` then the `schedules.yml` used by the container is missing or not mounted; verify the `scheduler` container has `/app/schedules.yml` file.

## What to paste to the epic / here if things fail
- `scheduler-logs.txt` (full scheduler logs)
- One example job stdout/stderr showing the failure
- Any JSON backfill reports
- Output of `ls -la /app/config` and `cat /app/schedules.yml` inside the scheduler container

---

Good luck — run the steps and paste any failing logs here and I will interpret them and propose fixes.
