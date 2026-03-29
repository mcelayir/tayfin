# tayfin-bff

**Purpose:** Backend-For-Frontend HTTP proxy that serves the Tayfin UI.  
**Context:** `tayfin-app`  
**Port:** 8030 (per ARCHITECTURE_RULES §6)

## Architecture

The BFF has **no database**. It proxies all data requests to the upstream bounded-context APIs:

| Upstream API         | Base URL (default)        | Client class      |
|----------------------|---------------------------|--------------------|
| tayfin-screener-api  | `http://127.0.0.1:8020`   | `ScreenerClient`   |

Architecture rules enforced:
- UI calls **only** the BFF (§2.2)
- BFF calls context APIs over HTTP (§2.1) — never reads their databases

## Endpoints

| Method | Path                    | Description                            |
|--------|-------------------------|----------------------------------------|
| GET    | `/health`               | Liveness check                         |
| GET    | `/api/mcsa/dashboard`   | Latest MCSA scores — all tickers       |
| GET    | `/api/mcsa/<ticker>`    | Latest MCSA score — single ticker      |
| GET    | `/api/mcsa/range`       | MCSA scores over a date range          |

### Query Parameters

**`/api/mcsa/dashboard`:** `band`, `min_score`, `limit`, `offset`  
**`/api/mcsa/range`:** `ticker` (required), `from` (required), `to` (required)

## Project Structure

```
tayfin-bff/
├── scripts/
│   └── run_bff.sh          # Local dev launcher
├── src/
│   └── tayfin_bff/
│       ├── __init__.py
│       ├── __main__.py      # python -m tayfin_bff serve
│       ├── app.py           # Flask factory (create_app)
│       ├── cli/
│       │   ├── __init__.py  # Typer app + serve command
│       │   └── main.py
│       ├── clients/
│       │   ├── __init__.py
│       │   └── screener_client.py  # httpx wrapper
│       └── config/
│           ├── __init__.py  # YAML + dotenv loader
│           └── loader.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_mcsa_endpoints.py
├── requirements.txt
└── requirements-dev.txt
```

## Running Locally

```bash
# Option 1: shell script (installs deps, sets PYTHONPATH)
./scripts/run_bff.sh

# Option 2: Typer CLI
PYTHONPATH=src python -m tayfin_bff serve --port 8030

# Option 3: Flask CLI
PYTHONPATH=src flask --app tayfin_bff.app run --port 8030
```

## Environment Variables

| Variable                           | Default                    | Description            |
|------------------------------------|----------------------------|------------------------|
| `TAYFIN_SCREENER_API_BASE_URL`     | `http://127.0.0.1:8020`   | Screener API base URL  |

## Examples & Schemas

Example curl (latest MCSA dashboard):

```bash
curl -sS "${TAYFIN_BFF_BASE_URL:-http://localhost:8030}/api/mcsa/dashboard?limit=20" \
	-H "Accept: application/json"
```

Example response schema (examples stored under `tests/fixtures` and client contracts under `src/tayfin_bff/clients`):

- Example fixtures: `tayfin-app/tayfin-bff/tests/conftest.py` and `tayfin-app/tayfin-bff/tests/test_mcsa_endpoints.py`
- Client contracts: `tayfin-app/tayfin-bff/src/tayfin_bff/clients/screener_client.py`

Notes for validators
--------------------
- Use the BFF tests and fixtures as authoritative examples when drafting README examples.
- Keep example payloads minimal and valid for automated JSON-schema validation when schemas are available.

## Tests

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

10 tests — health endpoint + all MCSA proxy endpoints with mocked upstream.
