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
The module follows repo-wide env conventions. Key env vars used by screener components include:

- `DATABASE_URL` — Postgres connection for migrations and persistence.
- `TAYFIN_CONFIG_DIR` — path to configuration files used by jobs and APIs.
- `TAYFIN_HTTP_TIMEOUT_SECONDS` — HTTP client timeout used when calling other services.

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
