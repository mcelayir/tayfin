---
template_version: 1
module: tayfin-ingestor-api
owner: "@dev"
qa_checklist: true
---

# tayfin-ingestor-api

This service exposes read-only HTTP endpoints over ingested instruments, fundamentals, and OHLCV data.

## Getting Started

Run the API locally (example):

```bash
./tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh
```

### Environment Variables (API)
| Key | Type | Required | Default | Example | Notes |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `DB_URL` | string | Yes | - | `postgres://user:pass@localhost:5432/tayfin` | SQL connection string used by the API |
| `JOB_RUN_ID` | string | No | - | `job-20260322-abc123` | Optional for read-only calls that want to attach provenance when triggering jobs |

## Endpoints

### `GET /health`
**Description:** Basic health probe.

**Response (200 OK):**
```json
{ "status": "ok" }
```

---

### `GET /fundamentals/latest`
**Query params:** `symbol` (required), `country` (optional, default `US`)

**Description:** Returns the latest fundamentals snapshot for a ticker.

**Example Request:**
```
GET /fundamentals/latest?symbol=AAPL
```

**Response (200 OK):**
```json
{
  "symbol": "AAPL",
  "country": "US",
  "as_of_date": "2026-03-21",
  "price": 183.45,
  "eps_ttm": 5.12,
  "bvps": 12.34,
  "pe_ratio": 35.8
}
```

**Notes / Schema:** Shapes are produced by `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/fundamentals_repository.py` — link here when adding an explicit JSON Schema.

**Curl Example**
```bash
curl -sS "http://localhost:5000/fundamentals/latest?symbol=AAPL" \
  -H "Accept: application/json"
```

---

### `GET /fundamentals`
**Query params:** `symbol` (required), `country` (optional), `from` (YYYY-MM-DD), `to` (YYYY-MM-DD), `limit` (int), `order` (`asc`|`desc`)

**Description:** Returns a range of fundamentals snapshots for a ticker.

**Response (200 OK):**
```json
{
  "symbol": "AAPL",
  "country": "US",
  "from": "2026-01-01",
  "to": "2026-03-21",
  "count": 45,
  "items": [ { "as_of_date": "2026-03-21", "price": 183.45, "eps_ttm": 5.12 }, ... ]
}
```

**Validation & Errors:** Returns `400` on invalid params and `404` when instrument not found. See `app.py` for exact error shapes.

---

### `GET /indices/members`
**Query params:** `index_code` (required), `country` (optional), `limit`, `order`

**Description:** Returns the list of instruments for an index code.

**Response (200 OK):**
```json
{ "index_code": "NDX", "country": "US", "count": 100, "items": [ { "ticker": "AAPL", "instrument_id": "..." }, ... ] }
```

---

### `GET /indices/by-symbol`
**Query params:** `symbol` (required), `country` (optional)

**Description:** Returns index memberships for the given symbol.

**Response (200 OK):**
```json
{ "symbol": "AAPL", "country": "US", "count": 2, "items": [ { "index_code": "NDX" }, { "index_code": "SPX" } ] }
```

---

### `GET /ohlcv`
**Query params (latest mode):** provide exactly one selector: `ticker` OR `index_code` OR `market_code`  
**Query params (range mode):** `ticker` + `from` + `to` (date strings)

**Description:** Returns latest candle(s) or a date-range series for a ticker.

**Latest (ticker) Response (200 OK):**
```json
{ "ticker": "AAPL", "as_of_date": "2026-03-21", "open": 180.12, "high": 184.00, "low": 179.50, "close": 183.45, "volume": 1234567 }
```

**Range Response (200 OK):**
```json
{ "ticker": "AAPL", "from": "2026-01-01", "to": "2026-03-21", "count": 60, "items": [ {"as_of_date":"2026-03-21","open":180.12,"high":184.0,"low":179.5,"close":183.45,"volume":1234567}, ... ] }
```

**Serializer implementation:** See `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/serializers/ohlcv_serializer.py` for canonical output shapes (`serialize_candle`, `serialize_series`).

**Curl Examples**
```bash
# Latest candle
curl -sS "http://localhost:5000/ohlcv?ticker=AAPL"

# Range
curl -sS "http://localhost:5000/ohlcv?ticker=AAPL&from=2026-01-01&to=2026-03-21"
```

---

### `GET /markets/instruments`
**Response:** Not implemented (501). The API returns a `501` until exchange listings ingestion is implemented.

## Schema Linkage

Where possible link to repository code as the authoritative model:

- Fundamentals repository: `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/fundamentals_repository.py`  
- OHLCV serializers: `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/serializers/ohlcv_serializer.py`

When adding inline JSON Schema, place it under `tayfin-ingestor/tayfin-ingestor-api/schemas/` and reference it from this README.

## QA Checklist
- [ ] Run `curl` examples against local dev and verify response shapes.  
- [ ] Validate that `serialize_candle` outputs match documented fields exactly.  
- [ ] Ensure error cases (missing params, invalid dates) return documented error codes.

## Links
- App: `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/app.py`  
- Serializers: `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/serializers/ohlcv_serializer.py`  
- Repositories: `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/repositories/`  

---

*Add inline JSON Schemas or files under `schemas/` as a follow-up if desired.*
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
