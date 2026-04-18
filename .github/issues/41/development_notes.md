# Development Notes: Issue #41 — BIST Discovery Job

## Branch
`feature/issue-41-bist-discovery`

---

## Work Log

### Story 1: Add `tradingview-screener==2.5.0` dependency
- **Status:** Completed
- **Commit:** `e0d94e4`
- **What was done:** Appended `tradingview-screener==2.5.0` to `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`. Installed and verified with `pip show tradingview-screener` confirming version `2.5.0`. No other `requirements.txt` was touched.
- **Decisions taken:** None — plan was explicit.
- **Deviations from plan:** None.
- **Blockers / surprises:** None. Package installs cleanly alongside existing `tradingview-scraper`.

---

### Story 6: Add spike script for `tradingview-screener==2.5.0`
- **Status:** Completed
- **Commit:** `01957c9`
- **What was done:** Created `tests/spikes/test_tradingview_screener_spike.py` with 4 assertions. Ran against live TradingView API — all 4 passed. Created knowledge doc at `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md`.
- **Spike findings:** 630 symbols returned for `market='turkey'`. All 630 are prefixed with `BIST:`. No auth required. Call latency < 1 second. Package import path is `from tradingview_screener import get_all_symbols`.
- **Decisions taken:** Created `tests/spikes/` directory (did not exist). Used `@pytest.mark.spike` for discoverability — this produces a `PytestUnknownMarkWarning`; this is cosmetic and expected without registering the custom mark.
- **Deviations from plan:** None.
- **Blockers / surprises:** None.

---

### Story 2: Implement `TradingViewBistDiscoveryProvider`
- **Status:** Completed
- **Commit:** `9481c20`
- **What was done:** Created `src/tayfin_ingestor_jobs/discovery/providers/tradingview_bist.py` with `TradingViewBistDiscoveryProvider` class. Updated `providers/__init__.py` to include `"tradingview_bist"` in `__all__`. Verified all acceptance criteria: interface satisfied, prefix stripped, sorted, deduplicated, `RuntimeError` raised on empty input.
- **Decisions taken:** Constructor takes no parameters, mirroring `NasdaqTraderIndexDiscoveryProvider`. No `instrument_type` key is set in returned dicts (plan-confirmed: `DiscoveryJob.run()` will get `None` via `it.get("instrument_type")`).
- **Deviations from plan:** None.
- **Blockers / surprises:** The `RuntimeError` test for empty input required patching at the module level _before_ instantiating the provider (the `importlib.reload` approach in the verification script would have incorrectly unbound the patch). Test used `with patch(target) as mock:` and instantiated a fresh provider inside the context — all assertions passed.

---

### Story 3: Register BIST provider in the factory
- **Status:** Completed
- **Commit:** `5fc0e1d`
- **What was done:** Added import for `TradingViewBistDiscoveryProvider` and an `elif code == "bist":` branch to `factory.py`. The NASDAQ-100 branch is untouched. Verified all three routes: `bist` → `TradingViewBistDiscoveryProvider`, `nasdaq100` → `NasdaqTraderIndexDiscoveryProvider`, empty cfg → `PlaceholderIndexDiscoveryProvider`.
- **Decisions taken:** None.
- **Deviations from plan:** None.
- **Blockers / surprises:** None.

---

### Story 4: Register BIST target in `discovery.yml` and verify CLI
- **Status:** Completed
- **Commit:** `41f386f`
- **What was done:** Appended `bist` entry to `config/discovery.yml` with `code: bist`, `country: TR`, `kind: market`, `index_code: BIST`, `name: "Borsa Istanbul"`. Verified `jobs list` shows both `nasdaq-100` and `bist`. Verified `target_cfg` dict matches expected structure exactly. Confirmed `nasdaq-100` entry is byte-for-byte identical to its prior state.
- **Decisions taken:** `kind: market` used (not `index`) per plan rationale — BIST represents a full market listing, not a single index.
- **Deviations from plan:** None.
- **Blockers / surprises:** The module entrypoint requires `PYTHONPATH=src` when run from the `tayfin-ingestor-jobs` directory. This matches the scheduler container's `PYTHONPATH` config in `docker-compose.yml`.

---

### Story 5: Unit tests for `TradingViewBistDiscoveryProvider`
- **Status:** Completed
- **Commit:** `e03f029`
- **What was done:** Created `tests/test_tradingview_bist_provider.py` with 8 unit tests. All 8 pass (`0 failures, 0 errors`). Tests cover: prefix stripping, alphabetical sort, deduplication, exact key set, `country`/`index_code` from config, `RuntimeError` on empty input, and a combined integration scenario.
- **Patch target used:** `"tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"` — matches the import binding in the provider module.
- **Decisions taken:** None.
- **Deviations from plan:** None.
- **Blockers / surprises:** None.

---

### Story 7: Register `discovery_bist_daily` in `infra/schedules.yml`
- **Status:** Completed
- **Commit:** `cf851b8`
- **What was done:** Added `discovery_bist_daily` entry after `discovery_daily` with `cron: "10 4 * * *"` and `cmd` using `/app/config/discovery.yml` (same as `discovery_daily` — config is copied into the container per OQ-1 resolution). Ran full infra test suite.
- **Decisions taken:** None.
- **Deviations from plan:** None.
- **Blockers / surprises:** Infra test suite shows 2 pre-existing failures on `main` before this PR's changes:
  1. `test_all_services_declared` — `scheduler` service present in `docker-compose.yml` but not in the test's `EXPECTED_SERVICES` set. **Pre-existing; not caused by this PR.**
  2. `test_db_vars_present[POSTGRES_PASSWORD-change_me]` — local `.env` has `tayfin_password` instead of `change_me`. **Pre-existing local dev environment mismatch; not caused by this PR.**
  The directly relevant test, `infra/tests/test_smoke_jobs.py::test_job_cli_list`, **passes**.

---

## Final Branch State

```
cf851b8  config(issue-41): add discovery_bist_daily schedule
e03f029  feat(issue-41): add unit tests for TradingViewBistDiscoveryProvider
41f386f  config(issue-41): add bist target to discovery.yml
5fc0e1d  feat(issue-41): register TradingViewBistDiscoveryProvider in factory
9481c20  feat(issue-41): implement TradingViewBistDiscoveryProvider
01957c9  feat(issue-41): add tradingview-screener spike and knowledge doc
e0d94e4  build(issue-41): add tradingview-screener==2.5.0 dependency
```

---

## Open Issues for QA Agent

1. **DB write verification (requires live DB):** The unit tests mock all network and DB calls. A full integration test where the job runs end-to-end against the dev database should verify:
   - `instruments` table contains BIST rows with `country = 'TR'`
   - `index_memberships` table contains rows with `index_code = 'BIST'`
   - `GET /indices/members?index_code=BIST&country=TR` returns tickers
   - NASDAQ-100 rows in `instruments` and `index_memberships` are untouched after the BIST job runs

2. **Idempotency check:** Run `jobs run discovery bist` twice in a row. Verify the instrument count does not double and `job_runs` shows two successful runs.

3. **OQ-2 (performance):** `DiscoveryJob._get_exchange_for_ticker` is called for every BIST ticker (~630). Each call makes a Stockdex/Yahoo network request. For Turkish tickers, these will all return `None` (exchange codes not in the mapping). This means ~630 unnecessary network calls per run. Not a correctness issue, but worth flagging for @lead-dev as a performance concern.

4. **Pre-existing infra test failures:** `test_all_services_declared` and `test_db_vars_present[POSTGRES_PASSWORD-change_me]` fail before and after this PR. Document these as pre-existing for whichever sprint resolves them.

---

## Open Issues for Lead Developer

1. **OQ-2 (performance / exchange resolution):** Should `DiscoveryJob._get_exchange_for_ticker` be skipped when `target_cfg["country"] != "US"` (or a non-US country)? Currently ~630 Stockdex/Yahoo calls will be made per BIST run, all returning `NULL`. A simple country-guard in `DiscoveryJob.run()` would eliminate them. This is out of scope for this story per the plan, but should be tracked.

2. **OQ-5 (schema confirmation):** No DB migration was needed — existing columns support any `country`/`index_code` values. Confirm this is acceptable or flag if an index or column addition is required.
