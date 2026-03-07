Copilot Task Planning Guide

This document instructs AI agents (GitHub Copilot or similar) how to break down new features or epics into structured implementation tasks for the Tayfin system.

The goal is to produce clear, safe, incremental implementation plans aligned with the project’s architecture and engineering principles.

Copilot must follow this document strictly when asked to plan a new feature.

⸻

1. Mandatory Architecture Reading

Before proposing ANY tasks you MUST read:
	•	docs/architecture/ARCHITECTURE_RULES.md
	•	docs/architecture/PHASE_0_DECISIONS.md
	•	docs/architecture/TECH_STACK_RULES.md
	•	docs/architecture/CODEBASE_CONVENTIONS.md

If a proposed plan violates any rule in those documents, the plan is invalid.

⸻

2. Hard Architecture Constraints (Non-Negotiable)

The Tayfin system follows strict bounded context architecture.

Copilot MUST enforce the following rules.

2.1 Context Ownership

Each bounded context owns its data.

Context	Owns
Ingestor	raw market data
Indicator	derived indicators
Screener	screening results
App	user interface and BFF

Forbidden

A context MUST NOT read another context’s database.

Examples of INVALID behavior:

❌ indicator job querying tayfin_ingestor.ohlcv

❌ screener querying tayfin_indicator.indicator_series

Correct behavior

✔ indicator jobs call ingestor API

✔ screener jobs call indicator API

⸻

2.2 Database Access

Rules:
	•	Only SQLAlchemy Core is allowed
	•	No SQLAlchemy ORM
	•	psycopg driver only

⸻

2.3 Job Execution Model

All jobs follow these rules:

Jobs are ephemeral processes.

They:
	1.	start
	2.	execute once
	3.	write results
	4.	exit

Jobs MUST NOT:
	•	run as long-lived workers
	•	keep background threads
	•	run loops waiting for events

⸻

2.4 Job Auditing

Every job MUST:

Create a record in:

job_runs

And a record per processed item in:

job_run_items

Example processing:

AAPL success
MSFT failed
NVDA success

Job outcome:

status = FAILED

Jobs must continue processing after item failures.

⸻

2.5 Idempotent Data Writes

All time-series writes MUST be idempotent.

This means deterministic upserts.

Example uniqueness key for indicators:

(ticker, as_of_date, indicator_key, params_json)

Running the same job twice must NOT create duplicates.

⸻

2.6 Migrations

Database schema changes MUST:
	•	use Flyway
	•	be placed in

<context>/db/migrations

Never modify schemas from application code.

⸻

3. Repository Structure

The repository is organized by bounded context.

Example:

tayfin-ingestor/
tayfin-indicator/
tayfin-screener/
tayfin-app/

Each context may contain:

<context>-jobs
<context>-api

 db/migrations

Jobs and APIs are separate deployable applications.

⸻

4. Task Design Principles

Tasks must be:
	•	small
	•	atomic
	•	independently testable
	•	architecture compliant

A single task must NOT:
	•	modify multiple bounded contexts
	•	mix migrations + complex business logic
	•	implement multiple algorithms
	•	introduce new frameworks

If a task grows beyond one clear responsibility, split it.

⸻

5. Standard Task Template

Each task must contain the following sections.

Title

Example

Task 6 — Compute SMA indicator series


⸻

Goal

Explain what the task accomplishes.

⸻

What Must Be Implemented

List exact files and behavior.

Example

Create:

 tayfin-indicator-jobs/src/.../sma_job.py


⸻

Constraints

Re-state critical architecture rules relevant to the task.

Example

Use SQLAlchemy Core
Call ingestor API for OHLCV
Do NOT query ingestor DB


⸻

Validation Steps

Every task must include reproducible commands.

Example

Run job
Verify database rows
Call API endpoint

Tasks without validation steps are invalid.

⸻

Commit Requirements

Every task must end with:
	•	semantic commit message
	•	push to epic branch

Example

feat(indicator): compute sma series


⸻

6. Epic Structure Pattern

A typical Tayfin epic should follow this order.

Task 1

Branch creation + skeleton

Task 2

Flyway migrations

Task 3

Data storage model

Task 4

Job framework

Task 5

External API client

Task 6+

Algorithms / ingestion

Later tasks

API endpoints

Final task

Tests + hardening

⸻

7. API Design Rules

APIs must:
	•	return JSON
	•	support latest queries
	•	support range queries
	•	avoid extremely large responses

Common endpoints:

/latest
/range
/index/latest


⸻

8. Testing Requirements

Every epic must include tests for:
	•	idempotent writes
	•	algorithm correctness
	•	failure path behavior
	•	API validation

Tests must NOT call external services.

External dependencies must be mocked.

⸻

9. Branch Strategy

Each epic starts with a new branch.

Example:

epic/vcp

Every task must:
	1.	commit changes
	2.	push to that branch

PR creation happens manually later.

⸻

10. Copilot Output Format

When asked to break down a feature:

Copilot must output:

Task 1
Task 2
Task 3
...

Each task must include:
	•	goal
	•	implementation details
	•	validation
	•	commit message

Copilot should NOT generate full instruction prompts unless asked.

⸻

11. Forbidden Behaviors

Copilot MUST NOT:
	•	invent new APIs
	•	read cross-context databases
	•	introduce new frameworks
	•	skip validation steps
	•	create massive multi-purpose tasks

If unsure about architecture, Copilot must ask for clarification instead of guessing.

⸻

12. Expected Behavior

When given a feature description Copilot must:
	1.	Identify the bounded context owning the feature
	2.	Determine migrations, jobs, APIs and tests required
	3.	Break the work into safe incremental tasks
	4.	Ensure every task can be validated independently

⸻

Final Instruction

When prompted with:

Break down this feature into implementation tasks

Copilot must follow this document strictly.