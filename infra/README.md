# Tayfin Infrastructure

Local-first Docker Compose stack for the Tayfin financial analysis platform.

## Quick Start

```bash
# 1. Create your .env from the template
cp .env.example .env          # edit POSTGRES_PASSWORD if needed

# 2. Bring up the full stack
docker compose -f infra/docker-compose.yml --env-file .env up -d --build

# 3. Verify all services are healthy
docker compose -f infra/docker-compose.yml --env-file .env ps
```

All services should show **healthy** (APIs) or **Exited (0)** (flyway).

Open [http://localhost:5173](http://localhost:5173) to access the UI.

## Service Inventory

| Service | Port | Image / Build | Description |
|---|---|---|---|
| **db** | 5432 | `timescale/timescaledb-ha:pg16` | TimescaleDB (PostgreSQL 16) |
| **flyway** | — | `flyway/flyway:12` | Run-once schema migrations |
| **ingestor-api** | 8000 | `tayfin-ingestor/tayfin-ingestor-api/` | Raw market data API |
| **indicator-api** | 8010 | `tayfin-indicator/tayfin-indicator-api/` | Technical indicator API |
| **screener-api** | 8020 | `tayfin-screener/tayfin-screener-api/` | Algorithmic screening API |
| **bff** | 8030 | `tayfin-app/tayfin-bff/` | Backend-for-Frontend |
| **ui** | 5173 | `tayfin-app/tayfin-ui/` | React/Vite dev server |

### Dependency Chain

```
db (TimescaleDB)
  └─ flyway (run-once migration)
       ├─ ingestor-api (:8000)
       │    └─ indicator-api (:8010)
       └─ screener-api (:8020)
            └─ bff (:8030)
                 └─ ui (:5173)
```

Health checks enforce this ordering — downstream services wait until their
dependencies report healthy before starting.

## Environment Variables

All configuration is via a single `.env` file at the repo root.
See [`.env.example`](../.env.example) for the full template.

### Database (ADR-05)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | DB hostname (`db` in Docker) |
| `POSTGRES_PORT` | `5432` | DB port |
| `POSTGRES_DB` | `tayfin` | Database name |
| `POSTGRES_USER` | `tayfin_user` | Application user (never `postgres`) |
| `POSTGRES_PASSWORD` | `""` (code) / `change_me` (.env.example) | DB password |

Docker Compose overrides `POSTGRES_HOST=db` for API containers via the
`environment:` block, so the `.env` value is only used for local non-Docker runs.

### Inter-Service URLs (ADR-05 §4)

| Variable | Local Default | Docker Compose Override |
|---|---|---|
| `TAYFIN_INGESTOR_API_BASE_URL` | `http://localhost:8000` | `http://ingestor-api:8000` |
| `TAYFIN_INDICATOR_API_BASE_URL` | `http://localhost:8010` | `http://indicator-api:8010` |
| `TAYFIN_SCREENER_API_BASE_URL` | `http://localhost:8020` | `http://screener-api:8020` |

### UI

| Variable | Docker Compose Value | Description |
|---|---|---|
| `VITE_API_TARGET` | `http://bff:8030` | Vite proxy target for `/api` routes |

## Common Operations

### Rebuild a single service

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d --build ingestor-api
```

### View logs

```bash
# All services
docker compose -f infra/docker-compose.yml --env-file .env logs -f

# Single service
docker compose -f infra/docker-compose.yml --env-file .env logs -f bff
```

### Re-run Flyway migrations

```bash
docker compose -f infra/docker-compose.yml --env-file .env up flyway
```

### Reset the database (destructive)

```bash
docker compose -f infra/docker-compose.yml --env-file .env down -v
docker compose -f infra/docker-compose.yml --env-file .env up -d --build
```

The `-v` flag deletes the `pgdata_dev` volume, wiping all data.

### Stop everything

```bash
docker compose -f infra/docker-compose.yml --env-file .env down
```

## Health Checks

Each Python API has a `GET /health` endpoint. The Dockerfiles include a
`HEALTHCHECK` instruction that probes this endpoint every 10 seconds.

```bash
# Quick smoke test from host
curl http://localhost:8000/health   # ingestor-api
curl http://localhost:8010/health   # indicator-api
curl http://localhost:8020/health   # screener-api
curl http://localhost:8030/health   # bff
curl http://localhost:5173          # ui (returns HTML)
```

## Architecture References

| Document | Path |
|---|---|
| Containerization strategy | `docs/architecture/adr/ADR_03_DOCKER_CONTAINERIZATION.md` |
| API config strategy | `docs/architecture/adr/ADR_04_API_CONFIG_STRATEGY.md` |
| Env variable contract | `docs/architecture/adr/ADR_05_ENV_VAR_CONTRACT.md` |
| Default credentials | `docs/architecture/adr/ADR_06_DEFAULT_CREDENTIAL_POLICY.md` |
| Architecture rules | `docs/architecture/ARCHITECTURE_RULES.md` |

## Troubleshooting

### Flyway fails on first boot

Flyway includes a retry loop (10 attempts × 2s) to wait for the DB to accept
authenticated connections. If it still fails, restart it manually:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up flyway
```

### Port already in use

If a port is already bound (e.g., a local Flask process on 8000):

```bash
lsof -ti:8000 | xargs -r kill -9
```

### `POSTGRES_*` warnings on `docker compose config`

These appear if you run `docker compose config` without `--env-file .env`.
Always pass `--env-file .env` or the variables resolve to empty strings.
