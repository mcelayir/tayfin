# PHASE 0 DECISIONS (FROZEN)

This document captures the outcomes of Phase 0 (Architecture Lock-In).

It is the “what we decided” record.  
The “how to enforce it” rules live in `ARCHITECTURE_RULES.md`.

---

# 0. Goal and scope

Phase 0 goal:
- remove ambiguity
- establish strict boundaries
- define job, DB, migration, and reporting semantics
- ensure local-first execution is the primary constraint

Out of scope for Phase 0:
- authentication/authorization
- cloud deployment specifics (Cloud Run later)
- production hardening and scaling

---

# 1. Monorepo structure

Decision:
- single GitHub repository
- contexts separated at repo root level
- each context contains multiple apps (jobs + api; app context contains ui + bff)
- CI/CD can be controlled independently per app via GitHub Actions workflows

Contexts:
- `tayfin-ingestor` (jobs + api)
- `tayfin-screener` (jobs + api)
- `tayfin-analyzer` (jobs + api)
- `tayfin-app` (ui + bff)

---

# 2. Strict bounded contexts

Decision:
- strict bounded contexts are enforced
- there is NO shared domain/DTO/enums/contracts module across contexts
- cross-context duplication is allowed and preferred

Rationale:
- reduces coupling
- preserves autonomy
- prevents “shared module sprawl”

Example:
- ingestor and screener may both define “Stock”, but each owns its own representation.

---

# 3. Cross-context communication

Decision:
- all cross-context communication happens via HTTP APIs
- no DB side reads across schemas
- UI calls only BFF
- BFF may call any context API
- context APIs may call other context APIs if necessary (no enforced one-way graph)

Rationale:
- maintains ownership boundaries
- supports future deployment separation
- prevents shared DB becoming a hidden integration layer

---

# 4. Job execution semantics (0.3)

## 4.1 Job nature
Decision:
- jobs are ephemeral, run-once tasks (not daemons)
- a job starts, runs a single logical task, and exits

## 4.2 Jobs as composition roots
Decision:
- jobs orchestrate collaborators
- jobs do not contain SQL/HTTP client logic/heavy business logic
- side effects happen behind explicit interfaces (repositories/providers)

## 4.3 Failure behavior
Decision:
- jobs process items best-effort:
  - continue on item failure
  - record failures
- job run is marked FAILED if any item fails

## 4.4 Idempotency
Decision:
- jobs must be safe to re-run
- deterministic upserts backed by unique constraints
- standard natural key pattern (where applicable):
  - `(symbol, as_of_date, provider)`

## 4.5 Job auditing
Decision:
- every job run is audited to DB
- all written records include provenance via job run id
- manual CLI triggers generate “special ids” by creating a job run record first
  - i.e., manual execution is still a job run

---

# 5. Database and migrations (0.4)

## 5.1 Postgres
Decision:
- single Postgres instance for local-first suite

## 5.2 Schema naming & ownership
Decision:
- one schema per context, named after the context (best practices)
- each context owns its schema and writes only to it

## 5.3 Row provenance
Decision:
- each record includes:
  - `created_at`
  - `updated_at`
  - `created_by_job_run_id`
  - (recommended) `updated_by_job_run_id`

## 5.4 Flyway placement and execution
Decision:
- each context has its own migrations folder
- Flyway runs “centrally” (one operational runner), not per app
- Flyway history table is per schema (one history table per context schema)

## 5.5 Rollback policy
Decision:
- undo scripts required only for destructive changes
- non-destructive issues handled with forward migrations

---

# 6. Reporting (0.5)

## 6.1 Reporting creation
Decision:
- reports are created by jobs
- APIs do not compute reports; they only serve stored artifacts and exports

## 6.2 Canonical formats
Decision:
- canonical report format is:
  - JSON (required)
  - HTML snapshot (optional)
- exports (CSV/PDF/XLSX) are derived artifacts

## 6.3 Immutability and admin overwrite
Decision:
- reports are immutable once created
- new computations create new report records
- overwrite/upsert is allowed only via explicit maintenance operations (“admin”)
  - not a normal API operation (no auth yet)
  - implemented later as CLI/CI-gated operation with explicit `--force` semantics

## 6.4 File logging
Decision:
- if an export file is generated, it should be logged in DB with:
  - timestamps
  - report association

---

# 7. Local-first execution expectations

Decision:
- suite runnable via Docker Compose
- jobs must also be runnable from host CLI while Postgres runs in Docker
- configuration comes from env vars and config files (no hardcoded connection info)

---

# 8. Open items (intentionally deferred)

- exact folder layout and scaffolding (Phase 1)
- exact migration folder naming pattern (Phase 1/2)
- API endpoint catalog (Phase 1/4)
- scheduling mechanism choice (infra vs scheduler app) — remains undecided
  - job logic must remain schedule-agnostic

---

Phase 0 is complete when:
- these decisions are committed to the repository
- `ARCHITECTURE_RULES.md` exists and matches these decisions
- Phase 1 begins with repo skeleton implementation aligned to these rules
