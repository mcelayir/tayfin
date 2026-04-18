# Technical Debt: Upgrade `tradingview-screener` from 2.5.0 → 3.1.0

**Issue:** #41 follow-up  
**Raised by:** Lead Developer  
**Priority:** Low–Medium  
**Component:** `tayfin-ingestor-jobs` dependency

---

## Background

`tradingview-screener` was pinned at `==2.5.0` when it was introduced in Issue #41. This was the latest stable version available at the time, and it was validated via a spike (`tests/spikes/test_tradingview_screener_spike.py`) confirming:

- `get_all_symbols(market='turkey')` returns ~630 symbols
- All symbols are prefixed `BIST:`
- No authentication required
- Latency < 1 s

Version `3.1.0` is now available. This ticket tracks the upgrade.

---

## Motivation

| Reason | Detail |
|--------|--------|
| Bug fixes | Patch and minor releases between 2.5.0 and 3.1.0 may contain bug fixes relevant to market queries |
| API stability | The `get_all_symbols` interface should be confirmed unchanged; if the API surface shifts it is better to discover this in a controlled upgrade than during a surprise breakage |
| Security hygiene | Keeping dependencies current reduces exposure to known vulnerabilities in transitive packages |
| Future market coverage | 3.x may introduce new market identifiers or expanded symbol sets relevant to future screener targets |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `get_all_symbols` signature change | Low | Existing unit tests + re-run spike |
| `BIST:` prefix format change | Low | Spike validates prefix; unit tests assert strip logic |
| New transitive dependency conflicts | Low | Resolve with `pip-compile` on upgrade |
| Breaking change in 3.x major API | Medium (3.x is a minor bump from 2.x) | Read changelog; run full test suite |

---

## Upgrade Steps

### Step 1 — Spike: validate 3.1.0 against live API

Run the existing spike against 3.1.0 before committing to the upgrade:

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs
pip install "tradingview-screener==3.1.0"
pytest tests/spikes/test_tradingview_screener_spike.py -v
```

Confirm all 4 spike assertions pass:
- Symbol count ≥ 500
- All symbols prefixed `BIST:`
- No auth error
- Latency acceptable

### Step 2 — Review changelog

Check the [tradingview-screener releases](https://github.com/shner-elmo/TradingView-Screener/releases) for any breaking changes between 2.5.0 and 3.1.0. Pay particular attention to:

- `get_all_symbols` signature or return type changes
- Any renaming of the `market` argument values (e.g., `'turkey'` → `'tr'`)
- Removal of public APIs used in `tradingview_bist.py`

### Step 3 — Update pinned version

If the spike passes with no API changes:

```diff
# tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt
-tradingview-screener==2.5.0
+tradingview-screener==3.1.0
```

### Step 4 — Run full unit test suite

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs
pip install -r requirements.txt
pytest tests/ -v
```

All 8 tests in `test_tradingview_bist_provider.py` must pass (they mock `get_all_symbols` so they are insensitive to API changes, but they validate the provider logic is intact).

### Step 5 — Update the knowledge doc

If the API surface or symbol count changes, update `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` to reflect the 3.1.0 behaviour.

---

## Acceptance Criteria

- [ ] `tradingview-screener==3.1.0` is pinned in `requirements.txt`.
- [ ] All 4 spike tests pass against the live API with 3.1.0.
- [ ] All 8 `test_tradingview_bist_provider.py` tests pass.
- [ ] `TRADINGVIEW_SCREENER_GUIDE.md` updated with any behavioural differences found.
- [ ] No other tests in the `tayfin-ingestor-jobs` suite are broken.

---

## Rollback

If the upgrade breaks the live API call (spike fails), revert `requirements.txt` to `==2.5.0` and open a separate tracking issue for the upstream breaking change.
