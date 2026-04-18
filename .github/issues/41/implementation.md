# Implementation Plan: Issue #41 — BIST Discovery Job

---

## Codebase Findings

### NASDAQ-100 Reference Job

- **File:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/discovery_job.py`
- **Class:** `DiscoveryJob`
- **Interface / base class:** `IIndexDiscoveryProvider` (structural `Protocol` — not inherited; satisfied structurally).  
  File: `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/interfaces.py`  
  Signature: `def discover(self, target_cfg: dict) -> Iterable[dict]`
- **Parameterization:** `DiscoveryJob.from_config(target_cfg, global_cfg)` receives the YAML target block verbatim. Inside `run()`, it calls `create_provider(self.target_cfg)`. The factory reads `target_cfg["code"]`; the value `"nasdaq100"` (or `"nasdaq-100"`) selects `NasdaqTraderIndexDiscoveryProvider`. All other fields (`country`, `index_code`, etc.) are also read from `target_cfg` inside `DiscoveryJob.run()` as fallbacks when the provider `discover()` call does not include them in the returned dicts.
- **Provider factory:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/factory.py` — `create_provider(target_cfg: dict)` reads `target_cfg.get("code")`.
- **Providers live at:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/`

---

### `discovery.yml` — Current Full Structure

```yaml
jobs:
  discovery:
    nasdaq-100:
      code: nasdaq100
      country: US
      kind: index
      index_code: NDX
      name: "NASDAQ-100"
```

**Dispatch path:**  
CLI `jobs run discovery <target>` → `loader.load_config()` → `cfg["jobs"]["discovery"][target]` → `DiscoveryJob.from_config(target_cfg, cfg)` → `create_provider(target_cfg)` (reads `target_cfg["code"]`).

---

### DB Schema

#### `tayfin_ingestor.instruments` table

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | `uuid` | NOT NULL | PK, `gen_random_uuid()` |
| `ticker` | `text` | NOT NULL | stripped symbol, no exchange prefix |
| `country` | `text` | NOT NULL | two-letter country code (e.g. `US`, `TR`) |
| `instrument_type` | `text` | NULL | optional; `NULL` is acceptable |
| `exchange` | `text` | NULL | added in V4; optional |
| `created_at` | `timestamptz` | NOT NULL | |
| `updated_at` | `timestamptz` | NOT NULL | |
| `created_by_job_run_id` | `uuid` | NOT NULL | FK → `job_runs.id` ON DELETE RESTRICT |
| `updated_by_job_run_id` | `uuid` | NULL | FK → `job_runs.id` ON DELETE SET NULL |

**Unique constraint:** `uq_tayfin_ingestor_instruments_ticker_country` on `(ticker, country)`  
**Indexes:** `ticker`, `country`, `exchange`

#### `tayfin_ingestor.index_memberships` table

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | `uuid` | NOT NULL | PK, `gen_random_uuid()` |
| `index_code` | `text` | NOT NULL | e.g. `NDX`, `BIST` |
| `instrument_id` | `uuid` | NOT NULL | FK → `instruments.id` ON DELETE CASCADE |
| `country` | `text` | NOT NULL | denormalised country code |
| `effective_date` | `date` | NULL | optional membership effective date |
| `created_at` | `timestamptz` | NOT NULL | |
| `updated_at` | `timestamptz` | NOT NULL | |
| `created_by_job_run_id` | `uuid` | NOT NULL | FK → `job_runs.id` ON DELETE RESTRICT |
| `updated_by_job_run_id` | `uuid` | NULL | FK → `job_runs.id` ON DELETE SET NULL |

**Unique constraint:** `uq_tayfin_ingestor_index_memberships_index_instrument` on `(index_code, instrument_id)`  
**Indexes:** `index_code`, `instrument_id`

#### Relationship

`index_memberships.instrument_id` → `instruments.id` (FK with CASCADE DELETE).  
The API join query is: `index_memberships im JOIN instruments i ON im.instrument_id = i.id WHERE im.index_code = :index_code`.  
Query is filtered additionally by `i.country = :country` when the `country` param is supplied.

#### Write order (NASDAQ-100 reference)

Per `DiscoveryJob.run()` in the reference file, the sequence per ticker is:

1. **`InstrumentRepository.upsert(...)`** — upserts into `instruments` by `(ticker, country)`, returns `instrument_id` (uuid string).
2. **`IndexMembershipRepository.upsert(...)`** — upserts into `index_memberships` using the `instrument_id` returned in step 1.
3. **`JobRunItemRepository.upsert(...)`** — audit record in `job_run_items` keyed by `ticker`.

This order is mandatory because `index_memberships.instrument_id` is a FK referencing `instruments.id`.

---

### Discovery API

> The API layer does **not** have a dedicated "BIST" route. It is fully data-driven.

- **Members route:** `GET /indices/members`  
  Handler: `index_members()` in `tayfin-ingestor/tayfin-ingestor-api/src/tayfin_ingestor_api/app.py`
- **Query params:**
  - `index_code` (required) — passed directly to `IndexMembershipRepository.get_members(index_code.upper(), ...)`
  - `country` (optional, default `"US"`) — filters by `i.country` in the join query
  - `order` (optional, default `"asc"`)
  - `limit` (optional, default `200`, max `5000`)
- **Filter mechanism:** The repository performs a SQL join on `index_code` and, when `country` is provided, also filters by `i.country`. **No hardcoded market names exist in the API layer.** The endpoint is fully data-driven; it will return BIST tickers as soon as the `index_memberships` table contains rows with `index_code = 'BIST'` and `i.country = 'TR'`.
- **Required change for BIST:** **None in the API layer.** After the job runs and stores rows, the caller queries: `GET /indices/members?index_code=BIST&country=TR`. If `country` defaults to `US`, a BIST-only query should explicitly pass `country=TR`.

---

### TradingView → DB Field Mapping

| TradingView field | Transformation | `instruments` column | `index_memberships` column |
|-------------------|----------------|----------------------|---------------------------|
| symbol (e.g. `BIST:AKBNK`) | Strip `BIST:` prefix; `.strip().upper()` | `ticker` (e.g. `AKBNK`) | — |
| _(derived from `target_cfg["country"]`)_ | Value `"TR"` (from config) | `country` | `country` |
| _(derived from `target_cfg["index_code"]`)_ | Value `"BIST"` (from config) | — | `index_code` |
| _(not provided)_ | `None` | `instrument_type` = `NULL` | — |
| _(not provided)_ | `None` / attempted via `_get_exchange_for_ticker` | `exchange` = `NULL` or resolved value | — |
| _(not provided)_ | `None` | — | `effective_date` = `NULL` |

> **Exchange resolution note:** `DiscoveryJob._get_exchange_for_ticker` currently calls Stockdex/Yahoo and maps US exchange codes (`NMS`→`NASDAQ`, `NYQ`→`NYSE`, etc.). For Turkish tickers, this will almost certainly return `None` (Yahoo finance exchange codes for BIST are not in the mapping) and will be stored as `NULL`. This is safe — `exchange` is nullable. The developer agent must **not** modify `_get_exchange_for_ticker`; no exchange enrichment is expected for BIST in this story.

---

## Implementation Stories

---

### Story 1: Add `tradingview-screener==2.5.0` dependency

**Files to change:**
- `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`

**Exact change:**  
Append one line to `requirements.txt`:

```
tradingview-screener==2.5.0
```

The file currently ends at `tradingview-scraper` (no version pin). The new entry is a **distinct package** (`tradingview-screener`, different PyPI package) and must be added on its own line with the exact version pin `==2.5.0`. **Do not modify** the existing `tradingview-scraper` entry.

**No other `requirements.txt` file in the workspace is touched.**

**Acceptance criteria:**
- `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` contains the line `tradingview-screener==2.5.0`
- `pip install -r requirements.txt` completes without conflict in the ingestor-jobs venv
- No other `requirements.txt` in the workspace is modified

---

### Story 2: Implement `TradingViewBistDiscoveryProvider`

**Files to create:**
- `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/tradingview_bist.py`

**Files to update:**
- `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/__init__.py`  
  Current content: `__all__ = ["placeholder"]` — add `"tradingview_bist"` to the list.

**Class to create:** `TradingViewBistDiscoveryProvider`

**Interface to implement:** `IIndexDiscoveryProvider` (structural Protocol from `discovery/interfaces.py`).  
Required method signature: `def discover(self, target_cfg: dict) -> Iterable[dict]`

**Constructor:** Mirror `NasdaqTraderIndexDiscoveryProvider.__init__` exactly — no required arguments, no injected dependencies. The class constructor takes no parameters.

**Transformation logic inside `discover(self, target_cfg: dict)`:**

1. Import path: `from tradingview_screener import get_all_symbols`
2. Call: `raw: list[str] = get_all_symbols(market='turkey')`
3. Guard: if `raw` is empty or `None`, raise `RuntimeError("No symbols returned from TradingView for market='turkey'")` — mirrors the NASDAQ provider's behaviour on empty rows.
4. Strip prefix: for each symbol, strip the `"BIST:"` prefix with `symbol.replace("BIST:", "", 1).strip().upper()`. Skip any resulting empty strings.
5. Deduplicate: use `dict.fromkeys(tickers)` to preserve order then deduplicate.
6. Sort: `sorted(...)` alphabetically.
7. Read config: `country = target_cfg.get("country", "TR")`, `index_code = target_cfg.get("index_code", "BIST")`.
8. Build output: list of dicts `{"ticker": t, "country": country, "index_code": index_code}` — exactly three keys, no extras.
9. Log: `logging.info(f"Discovered {len(result)} tickers from TradingView for {index_code}")` — mirrors NASDAQ provider log.
10. Return the list.

**Do not** call Stockdex, yfinance, or any other library. Do not set `instrument_type` in the returned dicts (it will be `None` via `it.get("instrument_type")` in `DiscoveryJob.run()`).

**Acceptance criteria:**
- Class is importable as `from tayfin_ingestor_jobs.discovery.providers.tradingview_bist import TradingViewBistDiscoveryProvider`
- `discover({"country": "TR", "index_code": "BIST"})` returns a `list[dict]` where every dict has exactly the keys `ticker`, `country`, `index_code`
- No ticker starts with `"BIST:"`
- Tickers are sorted alphabetically (assert `result == sorted(result, key=lambda x: x["ticker"])`)
- No duplicates
- Raises `RuntimeError` when `get_all_symbols` returns an empty list

---

### Story 3: Register BIST provider in the factory

**Files to change:**
- `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/factory.py`

**Current state of the factory:**

```python
from ..discovery.providers.placeholder import PlaceholderIndexDiscoveryProvider
from ..discovery.providers.nasdaqtrader import NasdaqTraderIndexDiscoveryProvider

def create_provider(target_cfg: dict):
    if not target_cfg:
        return PlaceholderIndexDiscoveryProvider()

    code = str(target_cfg.get("code", "") or "").lower()
    if code in ("nasdaq100", "nasdaq-100"):
        return NasdaqTraderIndexDiscoveryProvider()

    return PlaceholderIndexDiscoveryProvider()
```

**Required change:**  
Add one import and one `elif` branch. The NASDAQ branch must not be touched.

```python
from ..discovery.providers.placeholder import PlaceholderIndexDiscoveryProvider
from ..discovery.providers.nasdaqtrader import NasdaqTraderIndexDiscoveryProvider
from ..discovery.providers.tradingview_bist import TradingViewBistDiscoveryProvider

def create_provider(target_cfg: dict):
    if not target_cfg:
        return PlaceholderIndexDiscoveryProvider()

    code = str(target_cfg.get("code", "") or "").lower()
    if code in ("nasdaq100", "nasdaq-100"):
        return NasdaqTraderIndexDiscoveryProvider()
    elif code == "bist":
        return TradingViewBistDiscoveryProvider()

    return PlaceholderIndexDiscoveryProvider()
```

**Acceptance criteria:**
- `create_provider({"code": "bist"})` returns a `TradingViewBistDiscoveryProvider` instance
- `create_provider({"code": "nasdaq100"})` still returns `NasdaqTraderIndexDiscoveryProvider`
- `create_provider({})` still returns `PlaceholderIndexDiscoveryProvider`

---

### Story 4: Register BIST target in `discovery.yml` and verify CLI

**Files to change:**
- `tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml`

**Exact config block to add** (append under `jobs.discovery`, leaving the `nasdaq-100` entry entirely untouched):

```yaml
jobs:
  discovery:
    nasdaq-100:
      code: nasdaq100
      country: US
      kind: index
      index_code: NDX
      name: "NASDAQ-100"
    bist:
      code: bist
      country: TR
      kind: market
      index_code: BIST
      name: "Borsa Istanbul"
```

**Field rationale:**
- `code: bist` — matched by `factory.py` to route to `TradingViewBistDiscoveryProvider`
- `country: TR` — Turkey ISO-3166-1 alpha-2; stored in both `instruments.country` and `index_memberships.country`
- `kind: market` — BIST is not an index like NASDAQ-100 but a full-market listing
- `index_code: BIST` — the value stored in `index_memberships.index_code`; used as the `index_code=BIST` query param on the API

**CLI invocation after this story:**
```bash
python -m tayfin_ingestor_jobs jobs run discovery bist --config config/discovery.yml
```

**Acceptance criteria:**
- `python -m tayfin_ingestor_jobs jobs list --config config/discovery.yml` prints both `nasdaq-100` and `bist`
- `python -m tayfin_ingestor_jobs jobs run discovery bist --config config/discovery.yml` dispatches `DiscoveryJob` with `target_cfg = {"code": "bist", "country": "TR", "kind": "market", "index_code": "BIST", "name": "Borsa Istanbul"}`
- The NASDAQ-100 entry is byte-for-byte identical to its current state

---

### Story 5: Unit tests for `TradingViewBistDiscoveryProvider`

**Files to create:**
- `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_tradingview_bist_provider.py`

**Test setup:**  
Use `unittest.mock.patch` (or pytest `monkeypatch`) to patch `tradingview_screener.get_all_symbols` — the import inside the provider module resolves to `tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols`.  
Patch target string: `"tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"`

**Test cases to implement:**

| Test name | Mock input | Assertion |
|-----------|------------|-----------|
| `test_strip_prefix` | `["BIST:AKBNK"]` | Returned dict has `ticker == "AKBNK"` |
| `test_sorted_alphabetically` | `["BIST:ZZZCO", "BIST:AKBNK", "BIST:THYAO"]` | `[r["ticker"] for r in result] == ["AKBNK", "THYAO", "ZZZCO"]` |
| `test_deduplication` | `["BIST:AKBNK", "BIST:AKBNK", "BIST:THYAO"]` | `len(result) == 2` |
| `test_dict_keys` | `["BIST:AKBNK"]` | Each dict has exactly (and only) keys `{"ticker", "country", "index_code"}` |
| `test_country_from_config` | `["BIST:AKBNK"]`, `target_cfg={"country": "TR", "index_code": "BIST"}` | `result[0]["country"] == "TR"` |
| `test_index_code_from_config` | `["BIST:AKBNK"]`, `target_cfg={"country": "TR", "index_code": "BIST"}` | `result[0]["index_code"] == "BIST"` |
| `test_raises_on_empty` | `[]` | `pytest.raises(RuntimeError)` |
| `test_combined` | `["BIST:ZZZCO", "BIST:AKBNK", "BIST:AKBNK", "BIST:THYAO"]` | 3 unique results, sorted, no prefix, correct keys |

**No database connection. No real network call. No `DiscoveryJob` instantiation.**

**Acceptance criteria:**
- All tests pass with `pytest tests/test_tradingview_bist_provider.py` from `tayfin-ingestor/tayfin-ingestor-jobs/`
- `--tb=short` output shows 0 failures, 0 errors

---

### Story 6: Add spike script for `tradingview-screener==2.5.0`

> Per the implementation-specialist skill, a spike against a new library is required before it can be used in production code. This story is a prerequisite gate for Stories 2–5 if the library has not previously been validated.

**Files to create:**
- `tayfin-ingestor/tayfin-ingestor-jobs/tests/spikes/test_tradingview_screener_spike.py`

**The spike must assert:**
1. `from tradingview_screener import get_all_symbols` — import succeeds
2. `result = get_all_symbols(market='turkey')` — call succeeds without authentication (confirmed: no auth/cookie required)
3. `isinstance(result, list)` is `True`
4. At least one element starts with `"BIST:"` — `any(s.startswith("BIST:") for s in result)`
5. `len(result) > 10` — sanity check that a meaningful number of symbols is returned

**The spike must not write to any database.**

**Acceptance criteria:**
- Spike runs against live TradingView API without error
- Developer agent documents actual symbol count in `docs/knowledge/tradingview_screener/` (new file, analogous to existing `docs/knowledge/` entries)
- Lead developer reviews spike output before merger of Story 2

---

### Story 7: Register `discovery_bist_daily` in `infra/schedules.yml`

**Files to change:**
- `infra/schedules.yml`

**Exact entry to add** (append after the existing `discovery_daily` block):

```yaml
discovery_bist_daily:
  cron: "10 4 * * *"
  cmd: "python -m tayfin_ingestor_jobs jobs run discovery bist --config /app/config/discovery.yml"
```

**Config path note:** The config is copied into the scheduler container at `/app/config/discovery.yml`. This is the same path convention already used by the existing `discovery_daily` entry — use it without modification.

**Cron offset:** `10 4 * * *` (10 minutes after the NASDAQ-100 discovery at `0 4 * * *`) to stagger scheduler load.

**Acceptance criteria:**
- `infra/schedules.yml` contains the `discovery_bist_daily` entry
- `infra/tests/test_smoke_jobs.py` (if it validates schedule entries) still passes
- All existing schedule entries are untouched

---

## Open Questions

| # | Question | Status | Blocking? | Owner |
|---|----------|--------|-----------|-------|
| OQ-1 | The `--config /app/config/discovery.yml` path: is it accessible inside the scheduler container? | **RESOLVED** — config is copied into the container; use the same path as `discovery_daily`. | ~~Yes~~ | @lead-dev |
| OQ-2 | `_get_exchange_for_ticker` will be called for every BIST ticker. Its exchange map covers only US codes, so all ~500+ Turkish tickers will yield `exchange = NULL` while still incurring a Stockdex/Yahoo network call per ticker. Should `_get_exchange_for_ticker` be skipped when `country != "US"`? | Open | No — data lands correctly; performance concern only | @lead-dev |
| OQ-3 | Does `get_all_symbols(market='turkey')` require a TradingView session cookie or API key? | **RESOLVED** — no auth required. No env var needed. | ~~Yes~~ | — |
| OQ-4 | Should `index_code` be `BIST` (exchange identifier) or `XU100` (BIST-100 index code)? | **RESOLVED** — use `BIST`. Canonical API query: `GET /indices/members?index_code=BIST&country=TR`. | ~~Yes~~ | @lead-dev |
| OQ-5 | No DB migration needed — confirm no additional column or index is required for BIST. | Open | No — existing schema is sufficient | @lead-dev (confirm) |

---

## Constraints for Developer Agent

- **Do NOT modify** the NASDAQ-100 provider (`nasdaqtrader.py`), its factory branch, or its `discovery.yml` entry.
- **Pin** `tradingview-screener` to exactly `==2.5.0` — no range, no caret, no tilde.
- **Distinct package warning:** `tradingview-screener` (new) ≠ `tradingview-scraper` (already in requirements). Do not confuse or consolidate these.
- **Write order is mandatory:** `instruments` upsert must succeed before `index_memberships` upsert for each ticker. The foreign key enforces this; violating the order will produce a FK violation at runtime.
- **Ticker format:** Store tickers without any exchange prefix (e.g. `"AKBNK"`, not `"BIST:AKBNK"`). This is consistent with how NASDAQ tickers are stored (e.g. `"AAPL"`, not `"NASDAQ:AAPL"`).
- **Country code:** Use `"TR"` (the value from `target_cfg["country"]`) — this is the value both written to `instruments.country` and used as the filter on `GET /indices/members?country=TR`.
- **Story dependency order:** Story 1 (requirements) → Story 2 (provider) → Story 3 (factory) → Story 4 (config) → Story 5 (tests) → Story 7 (scheduler). Story 6 (spike) can be run in parallel with Story 1 — it is no longer a blocking gate since OQ-3 (no auth required) and OQ-4 (`index_code=BIST`) are resolved. Its sole remaining purpose is to document actual symbol count.
- **No schema migration story is needed.** The current DB schema (V1–V5 migrations) already accommodates any `country` / `index_code` combination. If @lead-dev identifies a gap (OQ-5), a Story 8 must be created for the migration and added to the dependency chain before Story 4.
