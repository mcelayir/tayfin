# How to Run the BIST Discovery Job from the Repo Root

All commands below are run from the **repository root** (`/home/muratcan/development/github/tayfin`).

---

## Prerequisites

The Docker Compose stack must be running with at least `db` and `ingestor-api` healthy.

```bash
docker compose -f infra/docker-compose.yml ps
```

Expected: `ingestor-api` shows `(healthy)`. If the stack is not running:

```bash
docker compose -f infra/docker-compose.yml up -d db flyway ingestor-api
```

Wait ~30 seconds, then re-run `ps` to confirm healthy status.

---

## Step 1 — Run the BIST discovery job

The script handles environment loading, venv setup, PYTHONPATH, and job execution automatically.

```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_discovery.sh
```

**What the script does:**
1. Sources `.env` from the repo root (loads `POSTGRES_*` credentials)
2. Creates or reuses a dedicated venv at `tayfin-ingestor/tayfin-ingestor-jobs/.venv`
3. Installs `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` into that venv (if not already installed)
4. Sets `PYTHONPATH` to the jobs `src/` directory
5. Runs: `python -m tayfin_ingestor_jobs jobs run discovery bist --config tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml`

**Expected terminal output (abridged):**

```
Sourcing /path/to/.env
Using existing venv at .../tayfin-ingestor-jobs/.venv
Running discovery job (bist)
INFO  - job_run created: <uuid>
INFO  - provider: TradingViewBistDiscoveryProvider — fetching symbols for market=turkey
INFO  - discovered 630 symbols
INFO  - Exchange not found for AEFES    ← expected, see note below
INFO  - Exchange not found for AKBNK
... (one line per ticker)
INFO  - Job finished: SUCCESS | total=630 succeeded=630 failed=0
```

The "Exchange not found" lines are **expected and non-fatal** — the exchange lookup is a US-only mapping and returns NULL for Turkish tickers. Data is correctly written. See [follow-up-technical-debt-1.md](follow-up-technical-debt-1.md) for the planned fix.

The job will take **several minutes** due to ~630 Yahoo Finance network calls (one per ticker). This is the known performance issue tracked in the tech debt document.

---

## Step 2 — Validate in Chrome

Open each URL in Chrome. The `ingestor-api` is on port `8000`.

### 2a — Check all BIST members were stored

```
http://localhost:8000/indices/members?index_code=BIST&country=TR&limit=1000
```

**Expected response:**
```json
{
  "index_code": "BIST",
  "country": "TR",
  "count": 630,
  "items": [
    { "ticker": "AEFES", "country": "TR", "exchange": null },
    { "ticker": "AKBNK", "country": "TR", "exchange": null },
    ...
  ]
}
```

Verify: `count` is `630` and `exchange` is `null` (expected for Turkish tickers).

### 2b — Check a specific Turkish ticker exists

```
http://localhost:8000/indices/by-symbol?symbol=THYAO&country=TR
```

**Expected response:** a list that includes `"BIST"` as one of the returned index codes.

---

## Step 3 — Idempotency check (optional)

Run the job a second time:

```bash
./tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_discovery.sh
```

Then re-check:

```
http://localhost:8000/indices/members?index_code=BIST&country=TR&limit=1000
```

`count` must still be `630`. The job uses upserts — re-running it must not create duplicate rows.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: tayfin_ingestor_jobs` | PYTHONPATH not set | Use the script, not a bare `python` command |
| `could not connect to server` | DB not running | Run `docker compose -f infra/docker-compose.yml up -d db` |
| `ERROR: .env not found` | Running from wrong directory | Must run from repo root |
| `RuntimeError: No symbols returned` | TradingView API unreachable | Check internet connection; retry |
| API returns `404 not_found` after job run | Job may have failed silently | Check job log output for `FAILED` lines |
