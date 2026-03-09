# Architecture Decision Record: Docker Containerization Strategy

## Status

**Proposed**

## Context

The Tayfin platform is a local-first financial analysis suite (ARCHITECTURE_RULES §7). Today, Docker Compose runs only the database (TimescaleDB) and Flyway migrations. All five application services — ingestor-api (8000), indicator-api (8010), screener-api (8020), BFF (8030), and UI (5173) — are started manually via shell scripts.

This means:

- A developer must open 5+ terminal tabs and run each service individually.
- There is no single command to bring up the full stack.
- Inter-service communication relies on hardcoded `localhost` URLs.
- There is no standard Dockerfile pattern — none of the services have one.

The goal of this ADR is to decide two things:

1. **WSGI server** — How Python APIs run inside their containers.
2. **UI serving** — How the React/Vite frontend is served in Docker Compose.

---

## Decision 1 — WSGI Server: Flask Development Server

### Options Considered

#### Option A — Flask Development Server (`flask run`)

**Description:** Use the built-in Flask dev server with `--host 0.0.0.0` in each container. This matches the current `run_api.sh` scripts exactly.

**Pros:**

- Zero new dependencies — no gunicorn/uvicorn added to requirements.txt
- Matches existing run scripts, reducing cognitive gap
- Sufficient for local-first single-user development
- Auto-reload can be enabled via volume mounts during development
- Simpler Dockerfiles — no WSGI config files needed

**Cons:**

- Flask dev server is single-threaded by default (acceptable for local dev)
- Not suitable for production (but production hardening is explicitly deferred per ADR_00 §0)
- No graceful worker management

#### Option B — Gunicorn

**Description:** Run each Flask app under Gunicorn with 2–4 workers.

**Pros:**

- Production-grade multi-worker WSGI server
- Graceful shutdown and worker management
- Better concurrency under load

**Cons:**

- Adds `gunicorn` to every API's `requirements.txt` (new dependency)
- Requires a gunicorn config file or CLI flags per service
- Over-engineered for local single-user development
- Production deployment is out of scope for Phase 0 (ADR_00 §0)

### Decision

**Flask development server (`flask run`)** is adopted for local Docker containers.

**Rationale:** Phase 0 explicitly defers production hardening (ADR_00_PHASE_0_DECISIONS §0). The system is designed for local-first, single-user execution. Adding Gunicorn introduces unnecessary complexity for zero benefit in the current use case. When production deployment begins, a follow-up ADR will introduce Gunicorn or an alternative.

### Dockerfile Template (Python APIs)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

ENV PYTHONPATH=/app/src

EXPOSE <port>

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:<port>/health')"

CMD ["flask", "--app", "<package>.app", "run", "--host", "0.0.0.0", "--port", "<port>"]
```

Where `<package>` and `<port>` are:

| Service | Package | Port |
|---|---|---|
| ingestor-api | `tayfin_ingestor_api` | 8000 |
| indicator-api | `tayfin_indicator_api` | 8010 |
| screener-api | `tayfin_screener_api` | 8020 |
| bff | `tayfin_bff` | 8030 |

---

## Decision 2 — UI Serving: Vite Dev Server in Own Container

### Options Considered

#### Option A — Vite Dev Server with HMR in Own Container

**Description:** Run `npm run dev -- --host 0.0.0.0` in a Node.js container. Vite proxies `/api` requests to the BFF container. Full hot module replacement during development.

**Pros:**

- Best developer experience — instant HMR on file changes
- Matches existing local development workflow exactly
- UI and BFF remain separate containers (clean separation)
- Proxy config in `vite.config.ts` simply changes target from `127.0.0.1` to `bff` (Docker service name)

**Cons:**

- Requires a Node.js container image (~150MB)
- Source files must be available in the container (volume mount or COPY)
- Vite dev server is not suitable for production serving

#### Option B — BFF Serves Pre-Built UI Dist

**Description:** Build the UI first (`npm run build`), then mount `dist/` into the BFF container. BFF already has static file serving routes.

**Pros:**

- Simpler compose — no Node.js container needed at runtime
- Single entry point for UI + API at port 8030
- Closer to a production-like serving model

**Cons:**

- No HMR — every UI change requires a rebuild
- Terrible developer experience for frontend iteration
- Adds a build step dependency before `docker compose up`
- BFF container needs UI dist mounted or copied in

#### Option C — Docker Compose Profiles (Both)

**Description:** Use Docker Compose profiles: `dev` profile runs Vite HMR container, `prod` profile builds and serves via BFF.

**Pros:**

- Flexibility for both use cases
- Explicit separation of dev vs prod concerns

**Cons:**

- More complex compose file (profiles, build stages)
- Over-engineering for current Phase 0 scope
- Prod profile is premature — no production deployment yet

### Decision

**Vite dev server with HMR in its own container (Option A)** is adopted.

**Rationale:** The primary use case is local development. HMR is essential for frontend iteration speed. The BFF already serves static files from `dist/` for non-Docker or CI scenarios — that path remains available but is not the Docker Compose default. Production serving will be addressed in a future ADR when deployment is in scope.

### Dockerfile Template (UI)

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### Vite Config Change Required

The Vite proxy must target the BFF by Docker service name:

```typescript
// vite.config.ts — Docker-aware proxy
server: {
  port: 5173,
  host: true,  // bind to 0.0.0.0
  proxy: {
    '/api': process.env.VITE_API_TARGET || 'http://127.0.0.1:8030',
  },
},
```

In docker-compose, set `VITE_API_TARGET=http://bff:8030`.

---

## Docker Compose Networking Model

All services run on the default Docker Compose bridge network. Services discover each other by service name.

### Service Dependency Chain

```
db (TimescaleDB)
  └─ flyway (run-once migration)
       ├─ ingestor-api (port 8000)
       ├─ indicator-api (port 8010) → depends on ingestor-api
       └─ screener-api (port 8020)
            └─ bff (port 8030) → depends on screener-api
                 └─ ui (port 5173) → depends on bff
```

### Port Allocation

| Service | Container Port | Host Port | Rationale |
|---|---|---|---|
| db | 5432 | 5432 | Existing convention |
| ingestor-api | 8000 | 8000 | Existing convention |
| indicator-api | 8010 | 8010 | Existing convention |
| screener-api | 8020 | 8020 | Existing convention |
| bff | 8030 | 8030 | Existing convention |
| ui | 5173 | 5173 | Vite default |

All host ports match container ports for simplicity. This avoids port translation confusion during debugging.

---

## Consequences

- Every Python API gets a Dockerfile following the template above.
- UI gets a Node.js Dockerfile with Vite dev server.
- `docker compose up -d` brings up the entire stack.
- All services are accessible from the host browser at their respective ports.
- When production deployment is needed, a new ADR will introduce Gunicorn and a production UI build strategy.
- The `run_api.sh` / `run_bff.sh` scripts remain functional for non-Docker local development.
