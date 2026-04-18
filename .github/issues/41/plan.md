# Plan: Issue #41 — Implement BIST Discovery Job

## Issue Summary

Add a new discovery job for the Turkey/BIST market to `tayfin-ingestor-jobs`, following the same provider/factory/config pattern as the existing NASDAQ-100 job. The `tradingview_screener` library (pinned to `2.5.0`) is used to fetch all Turkey symbols; each returned symbol is prefixed with `BIST:` and must be stripped and sorted before storing. After the job runs, tickers must be queryable through the existing `GET /indices/members` endpoint on `tayfin-ingestor-api`.

---

## Delivery Increments

| # | Title | Goal | Depends On | Open Questions |
|---|-------|------|------------|----------------|
| 1 | Dependency spike — `tradingview-screener==2.5.0` | Verify `get_all_symbols(market='turkey')` returns the expected payload shape in this environment and document any gotchas | None | Does the call require auth/cookies? Does it respect rate limits? Should a timeout be injected? Is the library import `tradingview_screener` (underscore) or something else? |
| 2 | Add `tradingview-screener==2.5.0` to `requirements.txt` | Pin the new dependency in the ingestor-jobs package | Increment 1 spike confirms the library works | Is there an ADR required before adding this dependency? Does the Lead Developer approve version pinning at `2.5.0`? |
| 3 | Implement `TradingViewBistDiscoveryProvider` | New provider class that calls `get_all_symbols(market='turkey')`, strips `BIST:` prefix, deduplicates, sorts alphabetically, and returns `Iterable[dict]` matching the `IIndexDiscoveryProvider` interface | Increment 2 | What `index_code` should be used—`BIST` or something else (e.g. `XU100`)? What `country` code—`TR`? What `instrument_type` should be set (or `None`)? |
| 4 | Register `bist` in provider factory + add config target | Update `factory.py` to route `code == "bist"` to the new provider; add `bist` target to `config/discovery.yml` | Increment 3 | Confirm `target_cfg` key name (e.g. `bist` vs `bist-all`) to use in CLI invocations |
| 5 | Unit tests for the new provider | Pytest unit tests (no DB, no network) that mock `get_all_symbols` and assert prefix stripping, deduplication, alphabetical sort, and correct dict keys returned | Increment 3 | None |
| 6 | Add `bist-discovery` schedule to `infra/schedules.yml` | Register a recurring cron job for BIST discovery so it runs automatically alongside the NASDAQ-100 discovery job | Increment 4 | What cron cadence is desired for BIST (daily same as NASDAQ-100, or different)? |

---

## Increment Detail

### Increment 1: Dependency spike — `tradingview-screener==2.5.0`

**Goal:**  
Confirm that `tradingview_screener.get_all_symbols(market='turkey')` works in the ingestor-jobs Python environment, returns a list of strings like `["BIST:AKBNK", ...]`, and does not require authentication or break idempotency.

**Approach hint:**  
Create a spike script at `tayfin-ingestor/tayfin-ingestor-jobs/tests/spikes/test_tradingview_screener_spike.py`. Install `tradingview-screener==2.5.0` in the local venv and assert:
- The import path: `from tradingview_screener import get_all_symbols`
- The return type is a `list[str]`
- At least one element starts with `BIST:`
- The call completes within a reasonable timeout
Per the implementation-specialist skill, document findings in `docs/knowledge/` if non-obvious behaviour is discovered.

**Acceptance criteria:**
- Spike script can be run and passes without error
- Lead developer sign-off on library behaviour is recorded before Increment 2 proceeds
- If the library requires env vars (e.g. credentials), those are documented in `docs/knowledge/`

**Open questions:**
- Does `get_all_symbols` require a TradingView session cookie or auth token?
- What is the approximate symbol count for `market='turkey'`?
- Is there a network timeout parameter on the call?
- Is the import `tradingview_screener` (underscore package name) — confirm it is distinct from `tradingview-scraper` (already in `requirements.txt`)?

---

### Increment 2: Add `tradingview-screener==2.5.0` to `requirements.txt`

**Goal:**  
Update `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` with the pinned dependency so the Docker image build is reproducible.

**Approach hint:**  
Add exactly `tradingview-screener==2.5.0` (with double equals and version pinned) to the file. The existing `tradingview-scraper` entry must remain untouched — these are two different packages. Do not add to any other `requirements.txt` (bounded context isolation).

**Acceptance criteria:**
- `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` contains `tradingview-screener==2.5.0`
- No other `requirements.txt` file in the workspace is modified
- The ingestor-jobs Docker image builds successfully with the new dependency

**Open questions:**
- Has the Lead Developer approved this dependency addition? (Per implementation-specialist skill, an ADR entry or explicit approval is required before adding to `requirements.txt`.)

---

### Increment 3: Implement `TradingViewBistDiscoveryProvider`

**Goal:**  
Create the provider class that satisfies `IIndexDiscoveryProvider` and returns BIST tickers ready to be consumed by `DiscoveryJob`.

**Approach hint:**  
Create `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/tradingview_bist.py`.

The `discover(self, target_cfg: dict) -> Iterable[dict]` method must:
1. Call `get_all_symbols(market='turkey')` to obtain raw symbols.
2. Strip the `BIST:` prefix from each symbol (e.g. `"BIST:AKBNK"` → `"AKBNK"`).
3. Deduplicate using a set or `dict.fromkeys`.
4. Sort alphabetically.
5. Read `country` and `index_code` from `target_cfg` (with defaults `"TR"` and `"BIST"` respectively).
6. Return a list of dicts: `[{"ticker": ..., "country": ..., "index_code": ...}, ...]`.

Mirror the `NasdaqTraderIndexDiscoveryProvider` structure exactly (same `__init__` signature, same `discover` signature, same logging). Do **not** look up exchange via `Stockdex` — that is a NASDAQ-specific concern in `DiscoveryJob._get_exchange_for_ticker`.

**Acceptance criteria:**
- Class implements `discover(target_cfg: dict) -> Iterable[dict]`
- All returned dicts contain exactly the keys `ticker`, `country`, `index_code`
- Tickers have no `BIST:` prefix
- Tickers are sorted alphabetically
- No duplicates in output

**Open questions:**
- Should `instrument_type` be included in the returned dicts? (The NASDAQ provider omits it; `DiscoveryJob` falls back to `it.get("instrument_type")` which returns `None`.)
- If `get_all_symbols` returns an empty list, should the provider raise or return an empty iterable (check NASDAQ provider raises on empty)?

---

### Increment 4: Register `bist` in provider factory + add config target

**Goal:**  
Wire the new provider into the existing factory and declare the `bist` target in the YAML config so the CLI can invoke it.

**Approach hint:**

**`factory.py` change:**  
Import `TradingViewBistDiscoveryProvider` and add a branch: `if code == "bist": return TradingViewBistDiscoveryProvider()`. Mirror the pattern used for `"nasdaq100"` / `"nasdaq-100"`.

**`config/discovery.yml` addition:**
```yaml
jobs:
  discovery:
    nasdaq-100:
      # ... existing, DO NOT MODIFY
    bist:
      code: bist
      country: TR
      kind: market
      index_code: BIST
      name: "Borsa Istanbul"
```

**CLI invocation after this increment:**
```
python -m tayfin_ingestor_jobs jobs run discovery bist --config config/discovery.yml
```

**Acceptance criteria:**
- `factory.py` routes `code == "bist"` to `TradingViewBistDiscoveryProvider`
- `config/discovery.yml` has a `bist` entry
- `python -m tayfin_ingestor_jobs jobs list` shows the `bist` target
- The NASDAQ-100 target is untouched

**Open questions:**
- Should `kind` be `"market"` or `"exchange"` in the YAML? (NASDAQ-100 uses `"index"` — BIST here represents all listed instruments, not a specific index.)
- Is `index_code: BIST` the right code, or should it be `XU100` or another canonical code consistent with how the API will be queried?

---

### Increment 5: Unit tests for the new provider

**Goal:**  
Provide offline unit tests (no network, no DB) that verify the core transformation logic of `TradingViewBistDiscoveryProvider`.

**Approach hint:**  
Create `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_tradingview_bist_provider.py`.

Use `monkeypatch` or `unittest.mock.patch` to replace `get_all_symbols` with a canned list:
```python
["BIST:ZZZCO", "BIST:AKBNK", "BIST:AKBNK", "BIST:THYAO"]
```

Assert:
1. Each result dict has keys `ticker`, `country`, `index_code`.
2. No ticker starts with `BIST:`.
3. Results are sorted alphabetically by ticker.
4. Duplicates are removed (3 unique expected from the canned input above).
5. `country` and `index_code` match `target_cfg`.

**Acceptance criteria:**
- Tests pass with `pytest` in the ingestor-jobs environment
- No real network call is made
- No database connection is needed

**Open questions:**
- None (self-contained test, all inputs are mocked)

---

### Increment 6: Add `bist-discovery` schedule to `infra/schedules.yml`

**Goal:**  
Register BIST discovery as a recurring scheduled job so it runs automatically in the infra scheduler.

**Approach hint:**  
Add a new entry to `infra/schedules.yml` following exactly the pattern of the `discovery_daily` entry:

```yaml
discovery_bist_daily:
  cron: "0 4 * * *"
  cmd: "python -m tayfin_ingestor_jobs jobs run discovery bist --config /app/config/discovery.yml"
```

Note: the `--config` path uses the container-mounted path `/app/config/discovery.yml`, consistent with other entries.

**Acceptance criteria:**
- `infra/schedules.yml` contains the `discovery_bist_daily` entry
- The `cmd` string matches the CLI shape verified in Increment 4
- Existing schedule entries are untouched

**Open questions:**
- Should BIST discovery run at the same time as NASDAQ-100 discovery (`0 4 * * *`) or at a different time (e.g. after Turkish market close — around `14:30 UTC`)?
- Is the `discovery.yml` config mounted into the scheduler container? (Inspect `infra/docker-compose.yml` volume mounts.)

---

## Handoff Notes for Lead Developer Agent

- **Entry point to explore:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/factory.py` — this is where the new provider is wired in
- **Reference implementation:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/nasdaqtrader.py`
- **Interface to implement:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/interfaces.py` — `IIndexDiscoveryProvider.discover(target_cfg: dict) -> Iterable[dict]`
- **DB tables to write to:** `tayfin_ingestor.instruments` (upsert by `ticker, country`) and `tayfin_ingestor.index_memberships` (upsert by `index_code, instrument_id`) — no new migration required
- **Config file:** `tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml` — add `bist` target alongside `nasdaq-100`
- **Scheduler file:** `infra/schedules.yml` — add `discovery_bist_daily`
- **Key constraint:** `tradingview-screener==2.5.0` is a **new** package distinct from `tradingview-scraper` (already in requirements). Do not confuse them. Pin exactly to `2.5.0` in `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` only.
- **Symbol transform:** `"BIST:AKBNK"` → strip prefix → `"AKBNK"`. Sort full list alphabetically before yielding.
- **No exchange enrichment:** `DiscoveryJob._get_exchange_for_ticker` uses Stockdex/Yahoo and is NASDAQ-specific. The BIST provider should yield `instrument_type=None`; the job will attempt exchange resolution per ticker via the existing `_get_exchange_for_ticker` method — whether this is desirable for Turkish stocks is an open question for `@lead-dev`.
- **Blocked decisions:** `index_code` value for BIST (`BIST` vs `XU100`), `kind` in YAML config, and scheduler cron time all require `@lead-dev` sign-off before Increment 4 is implemented.
