# tayfin-screener

Purpose
-------
The `tayfin-screener` context provides algorithmic scanning and screening of tickers using the project's signal definitions (e.g., VCP, MCSA). This README follows the canonical module template used across the repo and is intended to be machine-auditable for QA.

Scope
-----
- API: `tayfin-screener-api` — exposes screening endpoints and result shapes.
- Jobs: `tayfin-screener-jobs` — scheduled/one-off jobs that compute and persist screener results.
- DB: migrations and persisted result tables under `tayfin-screener/db/migrations`.

Artifacts
---------
- Inventory: See `tayfin-screener/artifacts.md` for source-of-truth files and locations.
- Schemas: API and persisted-row JSON Schemas will live under `tayfin-screener/*/schemas/`.

Quick Start (local)
-------------------
1. Install dependencies in the workspace virtualenv.
2. Read the API and Jobs READMEs before attempting to run services or jobs.

API
---
- Read the API-specific documentation at `tayfin-screener/tayfin-screener-api/README.md`.
- Typical endpoint: `GET /v1/screener/{strategy}/latest?ticker=SYMBOL`

Jobs
----
- Jobs live in `tayfin-screener/tayfin-screener-jobs` and follow the project Typer CLI conventions.
- All job writes must be linked to a `job_run_id`. See the jobs README for examples.

Environment variables (summary)
-------------------------------
The module follows repo-wide env conventions. Key env vars used by screener components include (example values shown):

- `DATABASE_URL` — Postgres connection for migrations and persistence. Example: `postgresql://tayfin:password@localhost:5432/tayfin_dev`
- `TAYFIN_CONFIG_DIR` — path to configuration files used by jobs and APIs. Example: `/srv/tayfin/config` or `./tayfin-screener/tayfin-screener-jobs/config`
- `TAYFIN_HTTP_TIMEOUT_SECONDS` — HTTP client timeout used when calling other services. Example: `10` (seconds)
- `TAYFIN_SCREENER_API_BASE_URL` — runtime base URL used in examples and tests. Example: `http://localhost:8083`
- `JOB_RUN_ID` — (optional) UUID used to force a provenance context for manual runs. Example: `2f1e6b10-3c4a-4d2a-9f5b-3a8b9d6c7e1f`

Example local config sequence
----------------------------
1. Start a local Postgres (or use the repo's Docker compose) and set `DATABASE_URL`.
2. Point `TAYFIN_CONFIG_DIR` at the screener job config folder used in README examples.
3. Set `TAYFIN_SCREENER_API_BASE_URL` when running API curl checks from CI or local scripts.

When adding README examples
--------------------------
- Use the example values above or minimal, valid placeholders so automated README validators can parse them.
- If a README contains interactive steps that require external services, clearly mark them as "integration-only" and include minimal mocks for unit tests.

Examples
--------
Minimal example JSON for a screener result (used in README examples and JSON Schema validation):

{
  "ticker": "AAPL",
  "strategy": "vcp",
  "as_of_date": "2026-03-28T00:00:00Z",
  "score": 0.82,
  "tags": ["vcp-breakout", "volume-confirmed"]
}

Validation & QA
---------------
- This module will include JSON Schema files for API responses and persisted rows under `*/schemas/`.
- Use the repo's README example validator (see `tayfin-indicator/tayfin-indicator-api/scripts/validate_examples.py`) once schemas are present.

Links
-----
- Artifacts inventory: [tayfin-screener/artifacts.md](tayfin-screener/artifacts.md)
- API README: [tayfin-screener/tayfin-screener-api/README.md](tayfin-screener/tayfin-screener-api/README.md)
- Jobs README: [tayfin-screener/tayfin-screener-jobs/README.md](tayfin-screener/tayfin-screener-jobs/README.md)

Next steps
----------
1. Populate `tayfin-screener/tayfin-screener-api/README.md` with endpoints and realistic examples (E36-05.3).
2. Populate `tayfin-screener/tayfin-screener-jobs/README.md` with run examples and provenance notes (E36-05.4).
3. Extract JSON Schemas and add a local validator script (E36-05.7..E36-05.8).
