# Architecture Decision Record: Default Credential Policy

## Status

**Proposed**

## Context

Across Tayfin's services, default database credentials are inconsistent:

| Service | Default User | Default Password |
|---|---|---|
| ingestor-api | `postgres` | `""` (empty) |
| indicator-api | `tayfin_user` | `""` (empty) |
| screener-api | `tayfin_user` | `tayfin_password` |
| ingestor-jobs | `tayfin_user` | `""` (empty) |
| indicator-jobs | `tayfin_user` | `""` (empty) |
| screener-jobs | `tayfin_user` | `""` (empty) |
| Docker Compose (db) | `tayfin_user` | `${POSTGRES_PASSWORD}` (from `.env`) |
| `.env.example` | `tayfin_user` | `change_me` |
| Flyway | `${POSTGRES_USER}` | `${POSTGRES_PASSWORD}` |

**Problems identified:**

1. **ingestor-api** defaults to `postgres` user — a superuser in PostgreSQL. Every other service defaults to `tayfin_user`.
2. **screener-api** is the only service with a non-empty default password (`tayfin_password`).
3. **Most services** default to an empty password, which silently connects if the database allows passwordless auth — a security anti-pattern even in local dev.
4. Docker Compose and Flyway correctly defer to env vars, but if a developer runs a service without `.env`, the Python defaults kick in and may not match the actual database credentials.

This ADR standardizes the default credential behavior for local development.

---

## Options Considered

### Option A — Hard-Coded Dev Defaults

**Description:** All services default to `tayfin_user` / `change_me`, matching `.env.example`.

**Pros:**

- Services work out of the box without any env setup — zero-friction for new developers.
- Consistent with `.env.example` and Docker Compose.

**Cons:**

- Hard-coded passwords in source code create a false sense of security.
- Risk of defaults leaking into non-dev environments if env vars are forgotten.

### Option B — Fail-If-Unset

**Description:** No default password. If `POSTGRES_PASSWORD` is not set, `get_engine()` raises an explicit error.

**Pros:**

- Forces explicit configuration — impossible to accidentally connect with wrong credentials.
- No credentials in source code whatsoever.

**Cons:**

- Higher friction for new developers — must create `.env` file before first run.
- Breaks zero-config local development story.

### Option C — Default User, No Default Password

**Description:** Default `POSTGRES_USER=tayfin_user` but `POSTGRES_PASSWORD` defaults to empty string. If auth fails, the database error surfaces immediately.

**Pros:**

- Matches the current majority pattern (5 of 7 services).
- User gets a clear database auth error if `.env` is missing.

**Cons:**

- Empty password may silently succeed if PostgreSQL `pg_hba.conf` allows `trust` auth (which Docker images often do locally).
- Less explicit than Option B.

---

## Decision

**Option A — Hard-Coded Dev Defaults** with the following constraints:

### Default Values

| Variable | Default Value | Rationale |
|---|---|---|
| `POSTGRES_USER` | `tayfin_user` | Dedicated application user, not superuser |
| `POSTGRES_PASSWORD` | `""` (empty string) | Matches Docker Compose local trust auth |
| `POSTGRES_HOST` | `localhost` | Local development |
| `POSTGRES_PORT` | `5432` | Standard PostgreSQL port |
| `POSTGRES_DB` | `tayfin` | Single database, schema-per-context |

### Rationale

- Tayfin is a **local-first** project (ARCHITECTURE_RULES §1). The primary deployment target is a developer's machine, not a production cloud.
- The Docker Compose `db` service uses `trust` authentication locally, so empty passwords work and are consistent with the TimescaleDB container defaults.
- The `.env.example` provides `change_me` as a reminder, but the code defaults to empty for zero-friction setup.
- Adding fail-if-unset (Option B) would break the local-first developer experience without meaningful security benefit — there is no production deployment yet.

### Mandatory Constraints

1. **No superuser defaults.** `POSTGRES_USER` must never default to `postgres`. The application user is `tayfin_user`.
2. **Consistency.** All services must use the exact same defaults. No service may invent its own default credentials.
3. **`.env.example` as documentation.** The root `.env.example` must always document every credential variable with realistic values.

---

## Implementation

### Engine Defaults (per ADR-05 template)

```python
user = os.environ.get("POSTGRES_USER", "tayfin_user")
password = os.environ.get("POSTGRES_PASSWORD", "")
```

### Required Migrations

| Service | Change |
|---|---|
| ingestor-api | Default user `postgres` → `tayfin_user` |
| screener-api | Default password `tayfin_password` → `""` |
| All others | Already compliant or will comply via ADR-05 engine template |

---

## Consequences

- All services connect with `tayfin_user` and empty password by default — identical to Docker Compose local setup.
- New developers can `docker compose up` and run any service without creating `.env` first.
- The `postgres` superuser default in ingestor-api is permanently retired.
- When/if Tayfin gains a production deployment, a new ADR will mandate `POSTGRES_PASSWORD` to be required (fail-if-unset) in production mode, likely via a `TAYFIN_ENV=production` guard. That ADR is out of scope for Phase 0.
