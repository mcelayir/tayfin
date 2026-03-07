# MCSA Epic — QA Validation Report

**Date:** 2026-03-07
**Branch:** `epic/mcsa`
**Target:** NASDAQ-100 (101 tickers)
**Run mode:** single-pass, partial missing-data mode (default)

---

## 1. Pipeline Execution

| Step | Result |
|---|---|
| Migration V3 applied | ✅ `tayfin_screener.mcsa_results` created (table + 3 indexes) |
| Docker DB healthy | ✅ `tayfin_db_dev` (TimescaleDB pg16) Up, healthy |
| Upstream Ingestor API (8000) | ✅ `{"status":"ok"}` |
| Upstream Indicator API (8010) | ✅ `{"status":"ok"}` (IPv4 only, see Known Issues) |
| Single-ticker smoke test (AAPL) | ✅ score=42, band=weak, evidence populated |
| Full pipeline (101 tickers) | ✅ 101 rows inserted, 0 errors |
| Screener API endpoints | ✅ all 3 MCSA endpoints verified |
| VCP API regression | ✅ `/vcp/latest/AAPL` returns expected result |
| Unit tests | ✅ **422 passed** (372 jobs + 50 API) in 1.47s |

## 2. Score Distribution

| Metric | Value |
|---|---|
| Total results | 101 |
| Score range | 4.55 – 69.85 |
| Mean score | 34.01 |
| as_of_date | 2026-03-07 (single date) |

### Band Distribution

| Band | Count |
|---|---|
| strong (≥85) | 0 |
| watchlist (≥70) | 0 |
| neutral (≥50) | 14 |
| weak (<50) | 87 |

**Observation:** No tickers reach "watchlist" or "strong" bands. This is expected
because fundamentals data is not yet ingested (fundamentals_score = 0 for all
101 tickers), capping the maximum achievable score at 80/100.

## 3. Component Scores

| Component | Non-zero count | Max weight | Notes |
|---|---|---|---|
| Trend (weight 30) | 79 / 101 | 30 | 13 tickers earned full 30 points |
| VCP (weight 35) | 101 / 101 | 35 | All have VCP results; 1 ticker ≥25 |
| Volume (weight 15) | 55 / 101 | 15 | 3 tickers earned full 15 points |
| Fundamentals (weight 20) | 0 / 101 | 20 | No fundamentals ingested yet |

## 4. Top 10 Tickers

| Ticker | Score | Band | Trend | VCP | Volume | Fundamentals |
|---|---|---|---|---|---|---|
| BKR | 69.85 | neutral | 30 | 24.85 | 15 | 0 |
| WMT | 65.90 | neutral | 30 | 25.90 | 10 | 0 |
| PEP | 63.45 | neutral | 30 | 23.45 | 10 | 0 |
| CSX | 62.75 | neutral | 30 | 22.75 | 10 | 0 |
| XEL | 61.35 | neutral | 30 | 21.35 | 10 | 0 |
| AEP | 56.00 | neutral | 30 | 21.00 | 5 | 0 |
| ADI | 55.30 | neutral | 30 | 20.30 | 5 | 0 |
| SBUX | 55.10 | neutral | 22 | 23.10 | 10 | 0 |
| CSCO | 53.45 | neutral | 30 | 23.45 | 0 | 0 |
| GILD | 53.10 | neutral | 30 | 23.10 | 0 | 0 |

## 5. Bottom 5 Tickers

| Ticker | Score | Band | Trend | VCP | Volume | Fundamentals |
|---|---|---|---|---|---|---|
| DASH | 4.55 | weak | 0 | 4.55 | 0 | 0 |
| INTU | 9.45 | weak | 0 | 9.45 | 0 | 0 |
| CPRT | 13.30 | weak | 0 | 13.30 | 0 | 0 |
| CSGP | 13.30 | weak | 0 | 13.30 | 0 | 0 |
| TEAM | 13.30 | weak | 0 | 13.30 | 0 | 0 |

## 6. Evidence JSON Validation

Sample (BKR — top scorer):

```json
{
  "vcp": {"score": 24.85, "vcp_score": 71.0, "pattern_detected": true},
  "band": "neutral",
  "trend": {
    "score": 30.0,
    "near_52w_high": true,
    "price_above_sma50": true,
    "sma50_above_sma150": true,
    "sma150_above_sma200": true,
    "distance_to_52w_high_pct": 0.0835
  },
  "volume": {
    "score": 15.0,
    "volume_dryup": true,
    "no_heavy_selling": true,
    "pullback_below_sma": true
  },
  "total_score": 69.85,
  "fundamentals": {
    "roe": null, "net_margin": null, "debt_equity": null,
    "revenue_growth_yoy": null, "earnings_growth_yoy": null,
    "score": 0.0
  }
}
```

All 101 rows have non-null `evidence_json`. Missing fields correctly reported
(all 5 fundamentals fields for every ticker).

## 7. API Endpoint Validation

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/mcsa/latest/<ticker>` | GET | ✅ 200 | Returns single result with evidence |
| `/mcsa/latest` | GET | ✅ 200 | Supports `band`, `min_score`, `limit`, `offset` |
| `/mcsa/latest?band=neutral` | GET | ✅ 200 | Band filter works, returns 14 items |
| `/mcsa/range?ticker=..&from=..&to=..` | GET | ✅ 200 | Date range query works |
| `/vcp/latest/AAPL` (regression) | GET | ✅ 200 | VCP endpoints unaffected |

## 8. Known Issues

| Issue | Severity | Notes |
|---|---|---|
| IPv6 connectivity | Low | Indicator/Ingestor APIs bind to `0.0.0.0` (IPv4 only). `httpx` resolves `localhost` to `::1` first. **Workaround:** use `http://127.0.0.1:PORT` in env vars. |
| No fundamentals data | Expected | Ingestor has no fundamentals endpoint data ingested yet. MCSA handles this gracefully (partial mode, score=0, fields listed in `missing_fields`). |
| No "strong"/"watchlist" bands | Expected | Ceiling is 80/100 without fundamentals. Highest scorer (BKR) at 69.85. |

## 9. Commit Log

| Hash | Description |
|---|---|
| `02e64bf` | Task 1: Branch + skeleton |
| `047e463` | Task 2: Migration V3 — mcsa_results |
| `267b6dd` | Task 3: MCSA + VCP read repositories |
| `4c40bb8` | Task 4: Extend IngestorClient |
| `bfdc0d0` | Task 5: MCSA config + defaults |
| `f3e53b0` | Task 6: MCSA scoring module |
| `323aca2` | Task 7: Volume assessment |
| `8ec3b94` | Task 8: MCSA screen job |
| `51733aa` | Task 9: Registry + wiring |
| `224c3d6` | Task 10: API endpoints |
| `7d42397` | Task 11: Unit tests (422 passing) |

## 10. Verdict

**QA PASSED** — All 101 NASDAQ-100 tickers scored, persisted, and served via
API. Scoring logic produces differentiated results across trend, VCP, and
volume components. Evidence JSON is complete and correctly structured.
Fundamentals will populate automatically once ingestor data is available.
