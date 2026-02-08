# GLOSSARY

Shared vocabulary for the Tayfin suite.

This glossary exists to align understanding.  
It does NOT define shared code or shared models.

---

# Bounded Context

A logical boundary within which:
- domain models
- rules
- terminology
- data ownership

are consistent.

In Tayfin:
- ingestor, screener, analyzer, and app are separate bounded contexts.

Key idea:
- same real-world concept can be modeled differently in each context.

---

# Context Sovereignty

The principle that each context:
- owns its schema
- owns its models
- owns its logic
- evolves independently

Other contexts interact via APIs, not via direct DB access.

---

# Job

An ephemeral, run-once process that:
- performs a single logical task
- processes a set of items
- audits its execution
- exits

Jobs are not daemons.

Examples:
- ingest NASDAQ fundamentals
- compute screening results
- generate a report

---

# Job Run

A single execution instance of a job.

A job run has:
- unique id
- start time
- end time
- status (SUCCESS/FAILED)
- audit data

All data writes are attributed to a job run.

Manual CLI executions are also job runs.

---

# Item (in a job)

The smallest processing unit inside a job.

Examples:
- one stock symbol
- one market
- one instrument

Jobs are atomic at item level:
- one item failure does not stop the whole run
- but the run is marked FAILED if any item fails

---

# Idempotency

The property that re-running the same job:
- does not corrupt data
- does not create duplicates
- leads to a consistent state

Achieved via:
- deterministic keys
- upserts
- unique constraints

---

# Upsert

A DB operation that:
- inserts if record does not exist
- updates if it already exists

Used to ensure idempotency.

---

# Provenance

Tracking where data came from.

In Tayfin this includes:
- created_at
- updated_at
- created_by_job_run_id
- updated_by_job_run_id (recommended)

Purpose:
- traceability
- debugging
- auditability

---

# Report

A structured artifact derived from domain data.

Created by jobs, not APIs.

Canonical format:
- JSON (primary)
- optional HTML snapshot

Exports:
- CSV
- PDF
- XLSX

---

# Canonical Format

The single source of truth representation.

For reports:
- JSON is canonical
- other formats are derived from it

---

# Export

A derived file representation of a report.

Examples:
- CSV
- PDF
- XLSX

Exports may be regenerated from canonical data.

---

# BFF (Backend-for-Frontend)

A backend service dedicated to serving the UI.

Responsibilities:
- aggregate data from multiple APIs
- shape responses for UI needs

UI talks only to BFF.

---

# Local-first

Design philosophy that prioritizes:
- local development
- Docker Compose execution
- minimal external dependencies

Cloud deployment is secondary.

---

# Flyway

A database migration tool.

In Tayfin:
- each context has its own migrations
- each schema has its own history table
- undo scripts required only for destructive changes

---

# Destructive Migration

A migration that:
- drops data
- renames structures
- cannot be safely reversed

Requires an undo script.

---

# When to extend this glossary

Add a term when:
- the team uses it often
- it has a specific meaning in Tayfin
- confusion appears in discussions

Do NOT add:
- general programming terms
- library-specific jargon
