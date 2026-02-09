Run the API locally:

```bash
# from repo root
PYTHONPATH=src flask --app tayfin_ingestor_api.app run --host 0.0.0.0 --port 8000
```

Examples:

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/fundamentals/latest?symbol=AAPL"
curl "http://localhost:8000/fundamentals?symbol=AAPL&from=2025-01-01&to=2026-02-09"

# Indices endpoints
```bash
curl "http://localhost:8000/indices/members?index_code=NDX"
curl "http://localhost:8000/indices/by-symbol?symbol=AAPL"
curl "http://localhost:8000/markets/instruments?market=NASDAQ"
```
```

Environment variables (defaults shown):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tayfin
DB_USER=tayfin
DB_PASS=
```
Purpose: Read-only API exposing ingested data.
Phase: Phase 1 skeleton (no business logic yet).
Context: tayfin-ingestor
