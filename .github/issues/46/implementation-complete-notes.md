# Implementation Complete Notes: Issue #46 — BIST OHLCV Ingestion Job

## Branch

`feature/issue-46-bist-ohlcv-job`

---

## Stories Completed

| # | Story | Commit SHA | Commit Message |
|---|-------|------------|----------------|
| Pre | Log pre-existing tech debt | `b6a245e` | `chore(issue-46): log pre-existing tech debt before implementation` |
| 1 | Add `bist` target to `config/ohlcv.yml` | `9d1e80f` | `config(issue-46): add bist ohlcv target to config/ohlcv.yml` |
| 2 | Add `bist` target to `config/ohlcv_backfill.yml` | `4c5e3f9` | `config(issue-46): add bist backfill target to config/ohlcv_backfill.yml` |
| 3 | Add BIST schedules to `infra/schedules.yml` | `c2f19bf` | `config(issue-46): add bist ohlcv daily and backfill schedules to infra/schedules.yml` |
| 4 | Add config completeness test | `944a956` | `feat(issue-46): add test asserting bist ohlcv config target field completeness` |

---

## Deviations from Plan

None. All four stories were implemented exactly as specified in `implementation.md`.

The implementation is purely configuration — no Python source files were created or modified. This is consistent with the spec finding that `OhlcvJob` and `run_ohlcv_ingestion` are fully generic and require zero code changes.

---

## Smoke Test Output

### Command to run job (Docker / local environment)

**Daily OHLCV ingestion (all BIST-100 instruments):**
```bash
python -m tayfin_ingestor_jobs jobs run ohlcv bist --config /app/config/ohlcv.yml
```

**With single-ticker override (validation / smoke test):**
```bash
python -m tayfin_ingestor_jobs jobs run ohlcv bist --ticker THYAO --config /app/config/ohlcv.yml
```

**With limit override (fast smoke test on first 3 tickers):**
```bash
python -m tayfin_ingestor_jobs jobs run ohlcv bist --limit 3 --config /app/config/ohlcv.yml
```

**Backfill (30-day window using chunk mode):**
```bash
python -m tayfin_ingestor_jobs jobs run ohlcv_backfill bist --days-back 30 --config /app/config/ohlcv_backfill.yml
```

**Prerequisite check (BIST-100 instruments must be present in DB):**
```sql
SELECT COUNT(*) FROM tayfin_ingestor.index_memberships im
JOIN tayfin_ingestor.instruments i ON im.instrument_id = i.id
WHERE im.index_code = 'BIST' AND i.country = 'TR';
-- Expected: ~100 rows (XU100 constituents)
-- If 0: run discovery job first:
--   python -m tayfin_ingestor_jobs jobs run discovery bist --config /app/config/discovery.yml
```

### API Endpoint to Validate Ingested Data

After the OHLCV job completes, validate via the ingestor API:

```
GET http://localhost:8000/ohlcv?index_code=BIST&country=TR
```

Or query the DB directly:

```sql
SELECT i.ticker, COUNT(*) AS candle_count, MIN(o.as_of_date) AS earliest, MAX(o.as_of_date) AS latest
FROM tayfin_ingestor.ohlcv_daily o
JOIN tayfin_ingestor.instruments i ON o.instrument_id = i.id
JOIN tayfin_ingestor.index_memberships im ON im.instrument_id = i.id
WHERE im.index_code = 'BIST' AND i.country = 'TR'
GROUP BY i.ticker
ORDER BY i.ticker
LIMIT 10;
```

### Config CLI validation output (offline, no DB)

```
$ python -m tayfin_ingestor_jobs jobs list --kind ohlcv
- nasdaq-100: code=ndx index_code=NDX timeframe=1d window_days=400
- bist: code=bist index_code=BIST timeframe=1d window_days=400

$ python -m tayfin_ingestor_jobs jobs list --kind ohlcv_backfill
- nasdaq-100: index_code=NDX default_exchange=NASDAQ default_chunk_days=30
- bist: index_code=BIST default_exchange=BIST default_chunk_days=30
```

### Config test output (offline, no DB, no network)

```
$ cd tayfin-ingestor/tayfin-ingestor-jobs && PYTHONPATH=src python -m pytest tests/test_bist_ohlcv_config.py -v

tests/test_bist_ohlcv_config.py::test_bist_ohlcv_target_exists PASSED
tests/test_bist_ohlcv_config.py::test_bist_ohlcv_required_fields PASSED
tests/test_bist_ohlcv_config.py::test_bist_ohlcv_default_exchange PASSED
tests/test_bist_ohlcv_config.py::test_bist_ohlcv_country_and_index_code PASSED
tests/test_bist_ohlcv_config.py::test_bist_ohlcv_timeframe PASSED
tests/test_bist_ohlcv_config.py::test_bist_backfill_target_exists PASSED
tests/test_bist_ohlcv_config.py::test_bist_backfill_required_fields PASSED
tests/test_bist_ohlcv_config.py::test_bist_backfill_default_exchange PASSED

8 passed in 0.04s
```

---

## Open Items / Follow-up

These are carried forward from `tech-debt-1.md` and `implementation.md` §6:

| ID | Item | Recommended Action |
|----|------|--------------------|
| TD-1 | `test_tradingview_bist_provider.py` mocks `get_all_symbols` which no longer exists in the provider. Tests pass by accident. | Separate bug-fix issue: rewrite mocks to patch `tradingview_screener.Query`; update `test_dict_keys` to assert 4 keys. |
| TD-2 | `default_exchange` absent from `nasdaq-100` `ohlcv.yml` entry (relies on hardcoded fallback). | Housekeeping: add `default_exchange: NASDAQ` to nasdaq-100 entries for explicit parity. |
| T1 | BIST instrument list in DB may be stale between discovery runs (XU100 rebalancing). | Future issue: add a live `BistLiveInstrumentResolver` that re-fetches from `Query().set_index('SYML:BIST;XU100')` at OHLCV job start. |
| T4 | No integration test for BIST OHLCV pipeline end-to-end (only config completeness test exists). | Future issue: add integration test after discovery job has been run against local DB. |
| T5 | No BIST targets in `tayfin-indicator` or `tayfin-screener` pipeline. | Separate issues per bounded context once OHLCV data is confirmed flowing. |
