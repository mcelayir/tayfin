Run the API locally:
# tayfin-ingestor-api

## Overview

Read-only Flask API that serves precomputed data from the `tayfin_ingestor` schema. The API does not compute anything on the fly — it reads what the ingestion jobs have written.

## How to run locally

```bash
# Helper script (installs deps + starts server on :8000)
./tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh

# Or manually
cd tayfin-ingestor/tayfin-ingestor-api
PYTHONPATH=src flask --app tayfin_ingestor_api.app run --host 0.0.0.0 --port 8000
```

DB credentials are read from the repo-root `.env` (or env vars `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`).

---

## Endpoints

### Health

```
GET /health → { "status": "ok" }
```

### Fundamentals

```
GET /fundamentals/latest?symbol=AAPL
GET /fundamentals?symbol=AAPL&from=2025-01-01&to=2026-02-09
```

### Index Memberships

```
GET /indices/members?index_code=NDX
GET /indices/by-symbol?symbol=AAPL
```

### OHLCV

A single `GET /ohlcv` endpoint with two modes:

#### Latest candle (no date params)

```
GET /ohlcv?ticker=AAPL
GET /ohlcv?index_code=NDX
```

- `ticker` — returns the single most recent candle for that ticker.
- `index_code` — returns the per-ticker latest candle for every index member, sorted by ticker ascending.

#### Date range (with from/to)

```
GET /ohlcv?ticker=AAPL&from=2025-06-01&to=2025-06-30
GET /ohlcv?ticker=AAPL&from=2025-06-01
```

- `ticker` required; at least one of `from`/`to` required.
- Items are sorted by `as_of_date` ascending.

---

### Example responses

**Latest by ticker:**

```bash
curl "http://localhost:8000/ohlcv?ticker=AAPL"
```

```json
{
  "ticker": "AAPL",
  "as_of_date": "2026-02-11",
  "open": 274.695,
  "high": 279.905,
  "low": 274.45,
  "close": 279.74,
  "volume": 15943723,
  "source": "tradingview"
}
```

**Date range:**

```bash
curl "http://localhost:8000/ohlcv?ticker=AAPL&from=2025-06-01&to=2025-06-05"
```

```json
{
  "ticker": "AAPL",
  "from": "2025-06-01",
  "to": "2025-06-05",
  "count": 4,
  "items": [
    { "ticker": "AAPL", "as_of_date": "2025-06-02", "open": 198.51, "high": 200.39, "low": 197.63, "close": 199.89, "volume": 46223840, "source": "tradingview" }
  ]
}
```

**Latest by index:**

```bash
curl "http://localhost:8000/ohlcv?index_code=NDX"
```

```json
{
  "index_code": "NDX",
  "count": 101,
  "items": [
    { "ticker": "AAPL", "as_of_date": "2026-02-11", "open": 274.695, "high": 279.905, "low": 274.45, "close": 279.74, "volume": 15943723, "source": "tradingview" },
    { "ticker": "ABNB", "as_of_date": "2026-02-11", "..." : "..." }
  ]
}
```

---

### OHLCV validation rules

| Condition | Status |
|---|---|
| No params | 400 |
| `ticker` + `index_code` together | 400 |
| Invalid date format | 400 |
| `from` > `to` | 400 |
| Unknown ticker | 404 |
| Unknown index (no OHLCV data) | 404 |

---

## Constraints

- Read-only — endpoints never write to the database.
- No authentication.
- No pagination yet.
- Consistent JSON shapes — candle keys are always `ticker`, `as_of_date`, `open`, `high`, `low`, `close`, `volume`, `source`. Numeric values are floats (volume is int).
