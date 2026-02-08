# Tayfin Monorepo

Local-first suite of services for ingesting market data, screening, analysis, and a user-facing app.

This repository is intentionally **structure-driven**:
- Strict bounded contexts (no shared domain/DTO code across contexts).
- Cross-context communication is **HTTP API only** (no DB side reads).
- Jobs are ephemeral, run-once, audited, and safe to re-run (idempotent upserts).

## What’s inside

### Contexts (root-level)
- `tayfin-ingestor/`
  - `tayfin-ingestor-jobs` — ingestion jobs (ephemeral run-once tasks)
  - `tayfin-ingestor-api` — read-only API over ingested data
- `tayfin-screener/`
  - `tayfin-screener-jobs` — screening jobs
  - `tayfin-screener-api` — read-only API over screening results
- `tayfin-analyzer/`
  - `tayfin-analyzer-jobs` — analysis jobs + report creation
  - `tayfin-analyzer-api` — read-only API over analysis and reports
- `tayfin-app/`
  - `tayfin-ui` — React UI
  - `tayfin-bff` — Backend-for-Frontend (UI gateway)

### Docs
- `docs/architecture/ARCHITECTURE_RULES.md` — non-negotiable rules (MUST/MUST NOT)
- `docs/architecture/PHASE_0_DECISIONS.md` — frozen decisions and rationale
- `docs/architecture/GLOSSARY.md` — shared vocabulary (terms only, not shared code)

## Local-first philosophy

This suite is designed to be:
- runnable via Docker Compose
- runnable partially (e.g., run a single job from CLI against Postgres in Docker)
- debuggable with deterministic, auditable job runs

Cloud deployment (GCP Cloud Run) is a later phase.

## Quick start (local)

Prerequisites:
- Docker + Docker Compose

1. Copy env file:

   cp .env.example .env

2. Start database:

   docker compose --env-file .env -f infra/docker-compose.yml up

3. The database will be available on localhost:5432.

## Key architecture rules (high level)

These are summarized here; the authoritative version is in `docs/architecture/ARCHITECTURE_RULES.md`.

### Strict bounded contexts
- No shared DTOs/enums/models between contexts.
- If two contexts represent the same concept (e.g., “Stock”), they do so independently.

**Example:**  
`tayfin-ingestor` may have its own `StockDTO`, and `tayfin-screener` may have a different `StockDTO`. They are not shared.

### Cross-context access is API-only
- Services and jobs MUST NOT read another context’s schema directly.
- Communication is via HTTP APIs.

**Example:**  
`screener-jobs` fetches required data by calling `ingestor-api`, not by querying `tayfin_ingestor.*` tables.

### Jobs are ephemeral + audited
- Jobs are run-once tasks that start, do work, audit, and exit.
- Jobs process items best-effort (continue on item failure) but the **run is marked FAILED** if any item fails.

**Example:**  
A “NASDAQ fundamentals ingestion” job continues processing other symbols even if one symbol fails, but the job run ends as FAILED if any failures occurred.

### Database: schema-per-context + Flyway per schema history
- One Postgres instance.
- One schema per context.
- Flyway history table per schema.
- Undo scripts required only for destructive migrations.

## Contributing & development notes

- Prefer clarity over cleverness.
- Keep jobs thin: jobs orchestrate; providers/repositories do real work.
- Avoid shortcuts that violate boundaries (especially “just read the DB directly”).

---

If you’re setting this up for the first time, start with:
1. `docs/architecture/ARCHITECTURE_RULES.md`
2. `docs/architecture/PHASE_0_DECISIONS.md`
