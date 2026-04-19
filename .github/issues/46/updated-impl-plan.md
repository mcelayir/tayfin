# Updated Implementation Plan: Issue #46 — BIST OHLCV Bulk Screener Provider

## Status of Previous Stories
Stories 1–4 from `implementation.md` are **complete and committed**.
This document supersedes the provider strategy for the BIST OHLCV job,
adding a new screener-based provider as the primary fetch mechanism.

---

## Problem Diagnosis: Why Only 11 Stocks Are Ingested

The current `TradingViewOhlcvProvider` uses the `tradingview-scraper`
WebSocket Streamer and is invoked **once per ticker** inside a serial loop in
`run_ohlcv_ingestion`. For BIST-100 (~100 instruments):

1. The service enters `_ingest_ticker` 100 times, each time opening a
   WebSocket connection to TradingView's streaming endpoint.
2. TradingView rate-limits or drops connections when requests arrive in rapid
   succession from the same IP. After approximately 11 connections succeed,
   subsequent ones fail with `TransientProviderError`, which retries, then
   falls through to yfinance, which also fails for BIST symbols under Yahoo's
   Turkish market quirks.
3. Result: only ~11 instruments succeed.

**Root cause:** 1 WebSocket connection per ticker × 100 tickers = 100
sequential connections. The `tradingview-screener` Query API resolves this
by fetching ALL instruments in **a single HTTP request**.

---

## Design Decision: Bulk-Fetch + Cache Provider Pattern

### Principle
The new `TradingViewScreenerOhlcvProvider`:
- On the **first** `fetch_daily` call: makes ONE `Query().get_scanner_data()`
  call fetching all BIST XU100 instruments at once.
- Caches the result in memory as `{bare_symbol: single-row DataFrame}`.
- **Subsequent** `fetch_daily` calls: served from cache — zero additional
  HTTP calls.
- Total HTTP calls for 100 BIST stocks: **1** (down from 100).

### Interface Contract
The new provider **implements the existing `IOhlcvProvider` Protocol
unchanged**. No changes to `_ingest_ticker`, `_fetch_with_fallback`, or
`normalize_ohlcv_df` are required. The existing per-ticker loop in the
service is preserved.

### Date Window Semantics
`tradingview-screener` returns only the **current day's OHLCV snapshot**.
It cannot return historical bars.

| Requested window | Provider behaviour | Fallback |
|-------------------|-------------------|---------|
| Window includes today (`end_date >= today`) | Bulk screener call → cache → return today's single row | None needed |
| Strictly historical (`end_date < today`) | Raises `ProviderEmptyError` immediately | `YfinanceOhlcvProvider` handles it |

This means:
- **Daily job** (`jobs run ohlcv bist`): 1 screener call for all 100 stocks,
  writes today's candle per instrument.
- **Backfill job** (`jobs run ohlcv_backfill bist`): all chunks have
  `end_date < today` → screener raises `ProviderEmptyError` → yfinance
  handles every chunk per ticker. Historical backfill works via existing
  yfinance path.
- **Last chunk of backfill that ends on today**: screener serves today's row
  from cache.

### Factory Pattern: Per-Market Provider Selection
A new `ohlcv_provider_factory(cfg)` function maps config → primary provider.
The service replaces the hardcoded `TradingViewOhlcvProvider()` instantiation
with a factory call. NASDAQ-100 gets `TradingViewOhlcvProvider()` exactly as
before.

---

## Updated Constraints

All constraints from `plan.md` and `implementation.md` remain in force.
The following are added:

| # | Constraint |
|---|-----------|
| C16 | `TradingViewScreenerOhlcvProvider` MUST implement the `IOhlcvProvider` Protocol in `ohlcv/providers/base.py` — same `fetch_daily` signature. |
| C17 | The screener provider MUST make exactly one `Query().get_scanner_data()` call per job run, regardless of how many tickers are requested. Results MUST be cached in memory on the provider instance. |
| C18 | The screener provider MUST raise `ProviderEmptyError` for any request where `end_date < date.today()` (i.e., purely historical windows), so `YfinanceOhlcvProvider` handles backfill. |
| C19 | `run_ohlcv_ingestion` in `service.py` MUST call `ohlcv_provider_factory(cfg)` to obtain the primary provider. The factory MUST return `TradingViewOhlcvProvider()` for `country != TR` or `index_code != BIST`. |
| C20 | `YfinanceOhlcvProvider` remains the universal fallback for ALL markets, including BIST. It is not replaced or removed. |
| C21 | The screener Query fields selected MUST use exact names from `references/fields.md`: `open`, `high`, `low`, `close`, `volume`. |
| C22 | The `date` column in the single-row DataFrame returned by the screener provider MUST be stamped with `str(end_date)` (the requested end date). `normalize_ohlcv_df` expects a `date` column (renamed to `as_of_date`). |
| C23 | `tradingview-screener==3.1.0` is already in `requirements.txt`. Do NOT add it again. |
| C24 | No changes to `config/ohlcv.yml` or `config/ohlcv_backfill.yml` are required for this stories. Config is already complete. |

---

## New Stories (Additions to Existing 4 Stories)

### Story 5 — Create `TradingViewScreenerOhlcvProvider`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/tradingview_screener_provider.py` | **New file** |

#### Class Specification

```
Class: TradingViewScreenerOhlcvProvider

Constructor:
    __init__(self, market: str, index_id: str)
        market:   tradingview-screener market identifier, e.g. 'turkey'
        index_id: SYML filter string, e.g. 'SYML:BIST;XU100'

Private state:
    _market: str
    _index_id: str
    _cache: dict[str, pd.DataFrame] | None   (None = not yet fetched)

Public method (satisfies IOhlcvProvider):
    fetch_daily(
        self,
        exchange: str,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 400,
    ) -> pd.DataFrame

        Logic:
        1. Resolve req_end = date.fromisoformat(end_date) if end_date else date.today()
        2. If req_end < date.today():
               raise ProviderEmptyError(
                   f"tradingview-screener has no historical bars for {symbol}; "
                   "end_date {req_end} is before today"
               )
        3. If self._cache is None: self._cache = self._fetch_all()
        4. df = self._cache.get(symbol.upper())
        5. If df is None:
               raise ProviderEmptyError(
                   f"No screener data for {symbol} — not found in {self._index_id}"
               )
        6. return df   # single-row DataFrame: columns = [date, open, high, low, close, volume]

Private method:
    _fetch_all(self) -> dict[str, pd.DataFrame]

        Logic:
        1. from tradingview_screener import Query, Column
        2. raw_count, raw_df = (
               Query()
               .set_markets(self._market)
               .set_index(self._index_id)
               .select('open', 'high', 'low', 'close', 'volume')
               .where(Column('is_primary') == True)
               .limit(500)
               .get_scanner_data()
           )
        3. If raw_df.empty: raise ProviderEmptyError("Screener returned empty DataFrame")
        4. today_str = str(date.today())
        5. cache = {}
           for each row in raw_df:
               bare_symbol = row['ticker'].split(':')[-1].upper()
               single_row_df = DataFrame with columns:
                   date=today_str, open=row['open'], high=row['high'],
                   low=row['low'], close=row['close'], volume=row['volume']
               cache[bare_symbol] = single_row_df
        6. log: "screener bulk fetch: raw_count={raw_count}, cached={len(cache)} symbols"
        7. return cache
```

#### Acceptance Criteria

1. Instantiating the provider makes zero HTTP calls.
2. The first `fetch_daily` call for any BIST ticker results in exactly one
   `Query().get_scanner_data()` call (confirmed via mock).
3. Subsequent `fetch_daily` calls for other tickers use cache — zero
   additional HTTP calls.
4. `fetch_daily` with `end_date` in the past raises `ProviderEmptyError`.
5. `fetch_daily` for a symbol not in the index raises `ProviderEmptyError`.
6. The returned DataFrame has exactly columns `[date, open, high, low, close, volume]`.
7. `normalize_ohlcv_df(result)` does not raise.

#### Exact Commit Message

```
feat(issue-46): add TradingViewScreenerOhlcvProvider with bulk-fetch cache
```

---

### Story 6 — Create `ohlcv/providers/factory.py`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/factory.py` | **New file** |

#### Function Specification

```
Function: ohlcv_provider_factory(cfg: dict) -> IOhlcvProvider

    Logic:
    1. country = str(cfg.get("country", "US")).upper()
    2. index_code = str(cfg.get("index_code", "")).upper()
    3. if country == "TR" and index_code == "BIST":
           return TradingViewScreenerOhlcvProvider(
               market="turkey",
               index_id="SYML:BIST;XU100",
           )
    4. return TradingViewOhlcvProvider()

Imports:
    from .tradingview_provider import TradingViewOhlcvProvider
    from .tradingview_screener_provider import TradingViewScreenerOhlcvProvider
```

**Extensibility note:** Routing is purely code-based. To add a new market in
future, add a new branch to this function. No config changes are needed.

#### Acceptance Criteria

1. `ohlcv_provider_factory({"country": "TR", "index_code": "BIST"})` returns
   a `TradingViewScreenerOhlcvProvider` instance.
2. `ohlcv_provider_factory({"country": "US", "index_code": "NDX"})` returns
   a `TradingViewOhlcvProvider` instance.
3. `ohlcv_provider_factory({})` returns a `TradingViewOhlcvProvider` instance
   (safe default).
4. `ohlcv_provider_factory({"country": "uk", "index_code": "UKX"})` returns
   a `TradingViewOhlcvProvider` instance (case-insensitive input handled).

#### Exact Commit Message

```
feat(issue-46): add ohlcv provider factory for per-market provider selection
```

---

### Story 7 — Refactor `service.py` to use `ohlcv_provider_factory`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/service.py` | **Existing — minimal edit** |

#### Changes Required

This is a **two-line change** in `run_ohlcv_ingestion`.

**Add import** at the top of `service.py`, alongside existing provider
imports:
```
from .providers.factory import ohlcv_provider_factory
```
Remove (or keep — see below) the direct import of `TradingViewOhlcvProvider`
if it is used nowhere else in the file. If it is used elsewhere, leave the
import. Check before removing.

**Replace** the hardcoded provider instantiation:
```python
# BEFORE (line approximately 340 in service.py):
tv_provider = TradingViewOhlcvProvider()
yf_provider = YfinanceOhlcvProvider()

# AFTER:
tv_provider = ohlcv_provider_factory(cfg)
yf_provider = YfinanceOhlcvProvider()
```

That is the entire change. Everything else — `_ingest_ticker`,
`_fetch_with_fallback`, `_compute_chunks`, audit logging, job_run_repo,
etc. — remains **completely untouched**.

#### Why this works for NASDAQ-100

`ohlcv_provider_factory({"country": "US", "index_code": "NDX"})` returns
`TradingViewOhlcvProvider()` — identical to the hardcoded value it replaces.
NASDAQ-100 behaviour is byte-for-byte unchanged.

#### Acceptance Criteria

1. `run_ohlcv_ingestion` called with the `nasdaq-100` config uses a
   `TradingViewOhlcvProvider` instance as the primary provider (confirmed via
   `isinstance` check in test or visual inspection).
2. `run_ohlcv_ingestion` called with the `bist` config uses a
   `TradingViewScreenerOhlcvProvider` instance as the primary provider.
3. The `yf_provider = YfinanceOhlcvProvider()` line is unchanged.
4. No other lines in `service.py` are modified.
5. The existing tests in `test_ohlcv_backfill_failure_paths.py` continue to
   pass (they inject fake providers directly into `run_ohlcv_ingestion` via
   the existing monkey-patch pattern — no impact).

#### Exact Commit Message

```
feat(issue-46): wire ohlcv provider factory into run_ohlcv_ingestion service
```

---

### Story 8 — Unit tests for `TradingViewScreenerOhlcvProvider`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_tradingview_screener_ohlcv_provider.py` | **New file** |

#### Test Specification

Mock target: `tradingview_screener.Query` — patch the full Query chain to
return a controlled `(int, pd.DataFrame)` tuple. Do NOT make real network
calls.

Patch target path:
```
tayfin_ingestor_jobs.ohlcv.providers.tradingview_screener_provider.Query
```

Helper fixture — a minimal mock screener DataFrame:
```
columns: [ticker, open, high, low, close, volume]
rows:    [BIST:AKBNK, 42.5, 44.0, 41.0, 43.2, 1500000]
         [BIST:THYAO, 310.0, 320.0, 305.0, 315.0, 8000000]
```

Test functions:

| Test | What it asserts |
|------|----------------|
| `test_fetch_daily_makes_one_bulk_call` | Calling `fetch_daily` for two different tickers calls `Query()` exactly once (cache reuse). |
| `test_fetch_daily_returns_correct_columns` | Returned DataFrame has exactly `[date, open, high, low, close, volume]`. |
| `test_fetch_daily_returns_correct_values` | `fetch_daily('BIST', 'AKBNK')` returns the correct OHLCV values from the mock. |
| `test_fetch_daily_strips_exchange_prefix` | `fetch_daily('BIST', 'AKBNK')` works even though mock ticker is `BIST:AKBNK`. |
| `test_fetch_daily_historical_raises` | `fetch_daily(end_date='2020-01-01')` raises `ProviderEmptyError`. |
| `test_fetch_daily_missing_ticker_raises` | `fetch_daily('BIST', 'UNKNWN')` raises `ProviderEmptyError`. |
| `test_normalize_accepts_provider_output` | `normalize_ohlcv_df(fetch_daily(...))` does not raise. |
| `test_factory_returns_screener_for_bist` | `ohlcv_provider_factory({"country": "TR", "index_code": "BIST"})` is a `TradingViewScreenerOhlcvProvider`. |
| `test_factory_returns_per_ticker_for_nasdaq` | `ohlcv_provider_factory({"country": "US", "index_code": "NDX"})` is a `TradingViewOhlcvProvider`. |

#### Acceptance Criteria

1. All tests pass with `PYTHONPATH=src pytest tests/test_tradingview_screener_ohlcv_provider.py -v`.
2. No real network calls. No DB connection.

#### Exact Commit Message

```
feat(issue-46): add unit tests for TradingViewScreenerOhlcvProvider and factory
```

---

## Story Summary Table (All 8 Stories)

| # | Story | Files | Commit |
|---|-------|-------|--------|
| 1 | Add `bist` to `ohlcv.yml` ✅ | `config/ohlcv.yml` | `config(issue-46): add bist ohlcv target to config/ohlcv.yml` |
| 2 | Add `bist` to `ohlcv_backfill.yml` ✅ | `config/ohlcv_backfill.yml` | `config(issue-46): add bist backfill target to config/ohlcv_backfill.yml` |
| 3 | Add BIST schedules to `schedules.yml` ✅ | `infra/schedules.yml` | `config(issue-46): add bist ohlcv daily and backfill schedules infra/schedules.yml` |
| 4 | Config completeness test ✅ | `tests/test_bist_ohlcv_config.py` | `feat(issue-46): add test asserting bist ohlcv config target field completeness` |
| 5 | New screener OHLCV provider | `ohlcv/providers/tradingview_screener_provider.py` (new) | `feat(issue-46): add TradingViewScreenerOhlcvProvider with bulk-fetch cache` |
| 6 | OHLCV provider factory | `ohlcv/providers/factory.py` (new) | `feat(issue-46): add ohlcv provider factory for per-market provider selection` |
| 7 | Wire factory into service | `ohlcv/service.py` (2-line edit) | `feat(issue-46): wire ohlcv provider factory into run_ohlcv_ingestion service` |
| 8 | Unit tests for provider + factory | `tests/test_tradingview_screener_ohlcv_provider.py` (new) | `feat(issue-46): add unit tests for TradingViewScreenerOhlcvProvider and factory` |

---

## Lead Dev Validation Checklist (Pre-Implementation)

1. Confirm `tradingview-screener==3.1.0` is in `requirements.txt` — **YES** (line 13).
2. Confirm `IOhlcvProvider` Protocol is in `ohlcv/providers/base.py` and
   the new provider's `fetch_daily` signature matches exactly.
3. Confirm `_fetch_with_fallback` in `service.py` uses `tv_provider` as first
   argument — yes, the factory replaces only the instantiation, not the call
   sites.
4. Confirm `normalize_ohlcv_df` requires `date` column (not `as_of_date`)
   as input — **YES** (`required = {"date", ...}` in normalize.py line 37).
   The screener provider must use column name `date` (not `as_of_date`).
5. Confirm `Column('is_primary') == True` filter is correct for deduplication
   — **YES** (established in Issue #41 tradingview_bist.py and skill examples).

---

## Follow-up Tech Debt (New)

| ID | Item |
|----|------|
| T6 | `TradingViewScreenerOhlcvProvider` only returns today's candle. Cold-start BIST OHLCV (first-ever run) will only write today's row. Historical BIST data requires running `ohlcv_backfill bist` which uses yfinance per-ticker. This is by design but should be documented in ops runbook. |
| T7 | The `ohlcv_provider_factory` hardcodes `market="turkey"` and `index_id="SYML:BIST;XU100"`. If a new market is ever added (e.g. Germany/DAX 40), a new branch must be added to the factory. Consider externalising these into the config (`screener_market`, `screener_index`) only when a second screener-backed market is added — YAGNI until then. |
