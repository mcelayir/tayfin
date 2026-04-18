# Technical Debt: Skip `_get_exchange_for_ticker` for Non-US Markets

**Issue:** #41 follow-up  
**Raised by:** Lead Developer  
**Priority:** Medium  
**Component:** `tayfin-ingestor-jobs` → `DiscoveryJob`

---

## Problem Statement

`DiscoveryJob._get_exchange_for_ticker` fires a live Stockdex/Yahoo Finance HTTP call for every ticker discovered. The internal exchange map it uses covers **US exchange codes only**:

```python
exchange_map = {
    "NMS": "NASDAQ", "NYQ": "NYSE", "ASE": "AMEX",
    "NCM": "NASDAQ", "PNK": "OTC", "OTC": "OTC",
    "PCX": "NYSE", "NGM": "NASDAQ", "BTS": "OTC"
}
```

For a BIST run (~630 Turkish tickers), Yahoo Finance returns exchange codes such as `IST` or raises an error entirely. None of these codes are in the map, so every call results in:

1. A network round-trip to Yahoo Finance (estimated 0.3–1.0 s per call)
2. A `None` return value
3. `exchange = NULL` stored in the `instruments` table

**Net effect:** ~630 unnecessary HTTP requests per BIST run, adding several minutes to job duration, with zero data benefit.

**Data correctness is not affected** — `exchange` is a nullable column and `NULL` is a valid value for non-US instruments.

---

## Root Cause

`_get_exchange_for_ticker` was designed for the NASDAQ-100 discovery job and is tightly coupled to the US exchange mapping. The `DiscoveryJob.run()` loop calls it unconditionally for every ticker regardless of the target market.

Relevant code in `discovery_job.py`:

```python
for it in items:
    ticker = it.get("ticker")
    country = it.get("country", self.target_cfg.get("country"))
    ...
    exchange = self._get_exchange_for_ticker(ticker)   # ← called for ALL tickers
    instrument_id = self.instrument_repo.upsert(
        ticker=ticker, country=country, exchange=exchange, ...
    )
```

---

## Proposed Fix

Add a country guard in `DiscoveryJob.run()` to skip the exchange lookup for non-US markets. Since the exchange map is US-only, any country other than `"US"` will always yield `NULL` — the lookup is provably wasted.

### Option A — Country guard (recommended)

```python
# In DiscoveryJob.run(), inside the for loop:
country = it.get("country", self.target_cfg.get("country"))
if country and country.upper() == "US":
    exchange = self._get_exchange_for_ticker(ticker)
else:
    exchange = None
```

**Pros:** Zero config change, immediately eliminates all BIST overhead. Correct by construction — if we ever support a non-US market that has exchange data, we'll need to build a separate enrichment path anyway.  
**Cons:** If a non-US market is later found to return valid Yahoo codes that _happen_ to match the US map, it would be skipped. Highly unlikely.

### Option B — Config flag `skip_exchange_lookup`

Add `skip_exchange_lookup: true` to `config/discovery.yml` under the `bist` target, and honour it in `DiscoveryJob.run()`.

**Pros:** Explicit, per-target control.  
**Cons:** More boilerplate; the current map is structurally US-only, so the flag would always need to be `true` for any non-US market. Over-engineered for the problem.

**Recommendation:** Option A. The country guard is derived directly from the exchange map's scope and requires no config changes.

---

## Acceptance Criteria

- [ ] `_get_exchange_for_ticker` is **not** called when `country != "US"`.
- [ ] NASDAQ-100 discovery job is **unaffected** (`country == "US"` path unchanged).
- [ ] Existing unit tests for `DiscoveryJob` still pass.
- [ ] New unit test: `run()` with a non-US `target_cfg` does not call `_get_exchange_for_ticker`.
- [ ] BIST job run time decreases measurably (no baseline required for acceptance, but log timing before/after).

---

## Scope & Dependencies

- **File to change:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/discovery_job.py`
- **Test file to update:** `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_discovery_job.py`
- **No schema changes.** No API changes. No new dependencies.
- **Out of scope for this ticket:** Implementing actual Turkish exchange enrichment (a separate ADR would be needed if that is ever desired).
