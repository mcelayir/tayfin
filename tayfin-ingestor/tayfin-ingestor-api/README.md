Run the API locally:
# tayfin-ingestor-api

Overview
- Read-only Flask API that serves precomputed data from the `tayfin_ingestor` schema.
- The API exposes snapshot and index membership data produced by the ingestor jobs; it does not compute fundamentals on the fly.

Implemented endpoints
- `GET /health` — basic health check returning `{ "status": "ok" }`.
- `GET /fundamentals/latest` — returns the latest snapshot for a symbol (by `symbol` + `country` + `source`).
- `GET /fundamentals` — range query for a symbol (from/to, limit, order).
- `GET /indices/members` — list index members for a given `index_code`.
- `GET /indices/by-symbol` — list indices that include a given symbol.

How to run locally

```
# from repo root
PYTHONPATH=src flask --app tayfin_ingestor_api.app run --host 0.0.0.0 --port 8000

# or use the helper script
./tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh
```

Example curl calls

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/fundamentals/latest?symbol=AAPL"
curl "http://localhost:8000/fundamentals?symbol=AAPL&from=2025-01-01&to=2026-02-09"
curl "http://localhost:8000/indices/members?index_code=NDX"
```

Data source
- The API reads only from the `tayfin_ingestor` schema (no cross-context DB access).
- It serves precomputed snapshots and index membership records produced by the jobs; it does not perform heavy calculations.

Constraints
- No authentication.
- Read-only: endpoints do not write to the database.
- Minimal business logic: the API performs simple filtering, ordering, and serialization to JSON.
- Responses are JSON and numeric values are returned as floats where applicable.
