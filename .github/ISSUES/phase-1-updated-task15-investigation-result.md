
# Phase 1 — Task 15.1 Investigation Result

Date: 2026-03-15

Summary
- **Root cause:** scheduler allowed screener jobs to start before ingestor finished populating instruments/OHLCV, causing many screener items to fail with "No OHLCV data". The immediate chain: `ohlcv` run initially failed (no instruments), `discovery` then populated instruments, but screener had already executed and failed.
- **Evidence:** scheduler logs and DB rows from the smoke test (see steps below).

Timeline (key log events vs DB rows)

| Source | Time (local in logs) | Time (DB / UTC) | Event |
|---|---:|---:|---|
| Scheduler logs | 2026-03-15 14:51:54 | 2026-03-15 13:51:54 UTC (DB ~13:51) | `[scheduler] executing module group: tayfin_ingestor_jobs` — started ingestor group |
| Scheduler logs | 2026-03-15 14:51:56 | 2026-03-15 13:51:55 UTC | `python -m tayfin_ingestor_jobs jobs run ohlcv ...` failed with ValueError: "No instruments found" |
| Scheduler logs | 2026-03-15 14:51:56 → 14:52:19 | 2026-03-15 13:51:57 → 13:52:19 UTC | `discovery` run executed and completed (populated instruments) |
| Scheduler logs | 2026-03-15 14:54:11 | 2026-03-15 13:54:11 UTC | Screener group executed; `vcp_screen` and many screener items ran — many failed with "No OHLCV data" |

DB queries executed (commands run)

```bash
docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema,table_name;"

docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT id, job_name, status, created_at, started_at, finished_at FROM tayfin_ingestor.job_runs ORDER BY created_at DESC LIMIT 50;"

docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT id, job_name, status, created_at, started_at, finished_at FROM tayfin_screener.job_runs ORDER BY created_at DESC LIMIT 50;"

docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT id, job_run_id, item_key, status, error_summary, created_at FROM tayfin_screener.job_run_items WHERE job_run_id = '504f4e69-3a97-485e-9df3-fd8f5d8675b7' ORDER BY created_at;"

docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT id, job_run_id, item_key, status, error_summary, created_at FROM tayfin_ingestor.job_run_items ORDER BY created_at DESC LIMIT 50;"
```

Selected DB findings (summary)

| Schema | Query result (high level) |
|---|---|
| tayfin_ingestor.job_runs | `discovery` and `fundamentals` show SUCCESS; `ohlcv` shows RUNNING/failed attempt around 13:51 UTC (matching the scheduler ohlcv failure in logs). |
| tayfin_screener.job_runs | `mcsa_screen` SUCCESS; `vcp_screen` FAILED (created 13:54:11 UTC). |
| tayfin_screener.job_run_items | For `vcp_screen` (job_run id 504f4e69...) many item rows show status=FAILED with `error_summary` = "ValueError: No OHLCV data for <TICKER>" — 101 failed items recorded. |

Key correlation / root-cause reasoning
- The scheduler logs show the ingestor `ohlcv` command failed early with ValueError: "No instruments found" (the job exits rc=1). The scheduler then runs `discovery` which populates instruments and completes successfully.
- The screener group ran later (13:54:11 UTC DB), but by that time ingestor had not completed a successful `ohlcv` ingestion for those tickers (the first `ohlcv` attempt failed and the run that populates OHLCV did not occur before screener started), so screener observed missing OHLCV and recorded per-ticker ValueErrors.
- Therefore the proximate cause of the many screener failures is ordering / timing: screener jobs executed while required ingestor data was not yet present.

Recommendations
- Enforce module-group sequencing in the scheduler so `tayfin_ingestor_jobs` completes before `tayfin_indicator_jobs`, and those complete before `tayfin_screener_jobs` run. This is exactly Task 15 (ingestor → indicator → screener). Implementation options:
  - Add an explicit ordered `module_order` in `infra/schedules.yml` and update `infra/scheduler/scheduler.py` to execute groups sequentially and wait for each group's subprocesses to finish (fail-fast or record group-level status).
  - Use DB advisory locks at module-group boundaries so multiple scheduler instances cannot race; lock acquisition should be attempted only once per group-run to avoid deadlocks.
  - Add a short retry/backoff for downstream jobs that depend on upstream data (e.g., screener checks if OHLCV exists for the target and waits/retries a few times before failing hard).

Commands I ran (for transparency)

| Step | Command |
|---|---|
| List non-system tables | `docker compose -f infra/docker-compose.yml --env-file .env exec db psql -U "${POSTGRES_USER:-tayfin_user}" -d "${POSTGRES_DB:-tayfin}" -c "SELECT table_schema,table_name FROM information_schema.tables ...;"` |
| Read recent ingestor job_runs | `... psql -c "SELECT ... FROM tayfin_ingestor.job_runs ORDER BY created_at DESC LIMIT 50;"` |
| Read recent screener job_runs | `... psql -c "SELECT ... FROM tayfin_screener.job_runs ORDER BY created_at DESC LIMIT 50;"` |
| Read screener job_run_items for failed vcp | `... psql -c "SELECT ... FROM tayfin_screener.job_run_items WHERE job_run_id = '504f4e69-...' ORDER BY created_at;"` |

Notes and caveats
- Timestamps in the scheduler logs appear in local time (14:51..14:54). DB timestamps are shown in UTC (13:51..13:54). The offset is consistent and has been accounted for in the timeline above.
- Some ingestor `ohlcv` runs show `RUNNING` in DB (created_at ~13:51:55 UTC); the initial `ohlcv` process failed quickly (per logs) before discovery populated instruments.

Next steps I can take (if you want me to proceed)
1. Implement scheduler sequential execution in `infra/scheduler/scheduler.py` (ingestor → indicator → screener) and add tests. (I can draft the patch and run unit tests.)
2. Add advisory-lock around module-group execution to prevent concurrent scheduler instances racing.
3. Add a lightweight retry for downstream jobs (screener) to check for required upstream data before failing.

File saved: [phase-1-updated-task15-investigation-result.md](.github/ISSUES/phase-1-updated-task15-investigation-result.md)
