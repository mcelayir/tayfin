# ARCHITECTURE RULES

This document defines the **non-negotiable architectural rules** of the Tayfin suite.

These rules use **MUST / MUST NOT / SHOULD** language intentionally.

If a change violates these rules, it is an architectural decision and must be made explicitly — not accidentally in code.

---

# 1. Bounded Contexts

## 1.1 Context sovereignty

Each context is sovereign.

A context MUST own:
- its domain concepts
- its DTOs and API models
- its database schema
- its migrations
- its business logic

A context MUST NOT:
- write into another context’s schema
- depend on another context’s domain models

---

## 1.2 No shared domain code

There MUST NOT be a shared domain/DTO/enums module across contexts.

Duplication between contexts is allowed and preferred over coupling.

**Example**

If both ingestor and screener represent a “Stock”:
- `tayfin-ingestor` defines its own model
- `tayfin-screener` defines its own model
- They are not shared

---

# 2. Cross-Context Communication

## 2.1 API-only rule

Cross-context data access MUST happen via HTTP APIs.

Services and jobs MUST NOT:
- query another context’s schema
- join across schemas
- rely on another context’s tables

**Example**

Correct:
- screener calls ingestor API

Incorrect:
- screener queries `tayfin_ingestor.stocks`

---

## 2.2 UI and BFF constraints

- UI MUST call only the BFF.
- BFF MAY call any context API.
- UI MUST NOT call context APIs directly.

---

# 3. Jobs

## 3.1 Job nature

A job is:
- ephemeral
- run-once
- atomic at item level
- a composition root

A job MUST:
- start
- perform a single logical task
- exit

Jobs MUST NOT be long-running daemons.

---

## 3.2 Responsibility separation

Jobs orchestrate.  
They MUST NOT contain:
- SQL
- HTTP client logic
- heavy business logic

Those belong in providers and repositories.

**Example**

Correct:
- Job calls `FundamentalsProvider` and `Repository`

Incorrect:
- Job runs raw SQL directly

---

## 3.3 Failure semantics

Jobs process items best-effort:
- continue on item failure
- record failures

A job run is marked FAILED if any item fails.

---

## 3.4 Idempotency

Jobs MUST be safe to re-run.

Deterministic upserts MUST be used with unique constraints.

Typical key:
- `(symbol, as_of_date, provider)`

---

## 3.5 Audit

Every job run MUST be audited in the database.

All writes MUST reference:
- `created_by_job_run_id`
- (recommended) `updated_by_job_run_id`

Manual CLI runs are still job runs and MUST create audit records.

---

# 4. Database

## 4.1 Schema-per-context

- One Postgres instance
- One schema per context
- Schema named after context

Examples:
- `tayfin_ingestor`
- `tayfin_screener`
- `tayfin_analyzer`

---

## 4.2 Table provenance

Tables MUST include:
- `created_at`
- `updated_at`
- `created_by_job_run_id`

This ensures traceability.

---

## 4.3 No cross-schema reads

Contexts MUST NOT read other schemas.

The database is NOT a shared read model.

---

# 5. Migrations (Flyway)

## 5.1 Ownership

Each context owns its migrations.

Migrations MUST modify only that context’s schema.

---

## 5.2 History tables

Each schema MUST maintain its own Flyway history table.

This preserves context isolation.

---

## 5.3 Rollbacks

Undo scripts are REQUIRED only for destructive changes:
- drops
- renames
- irreversible transformations

Non-destructive issues are fixed with forward migrations.

---

# 6. Reporting

## 6.1 Report creation

Reports MUST be created by jobs, not APIs.

APIs are read-only over reports.

---

## 6.2 Canonical format

Canonical report format:
- JSON (required)
- HTML snapshot (optional)

CSV/PDF/XLSX are derived exports.

---

## 6.3 Immutability

Reports are immutable once created.

New computations create new report records.

Overwrite/upsert is allowed only via explicit maintenance operations.

---

# 7. Local-First Execution

The system MUST be runnable locally:
- via Docker Compose
- or partial local execution (e.g., running a job from CLI)

Configuration MUST come from env vars or config files, not hardcoded values.

---

# 8. When in doubt

When a decision is unclear:
1. Prefer isolation over convenience
2. Prefer duplication over coupling
3. Prefer explicitness over magic
4. Document decisions

---

This document is the architectural constitution of the Tayfin suite.
