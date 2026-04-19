# Implementation Specification: Issue #46 — BIST OHLCV Ingestion Job

## Branch
`feature/issue-46-bist-ohlcv-job`

---

## Codebase Investigation Findings

### NASDAQ-100 OHLCV Job — Authoritative Reference

| Component | File | Key details |
|-----------|------|-------------|
| Job wrapper class | `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/ohlcv_job.py` | `OhlcvJob`; constructed via `OhlcvJob.from_config(target_cfg, global_cfg)` |
| Shared orchestration service | `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/service.py` | `run_ohlcv_ingestion(*, target_name, cfg, start_date, end_date, ...)` |
| CLI routing | `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/cli/main.py` | `jobs run ohlcv <target>` → loads `ohlcv.yml` → `cfg["jobs"]["ohlcv"][target]` → `OhlcvJob.from_config(target_cfg, cfg)` → `job.run()` |
| CLI list | same | `jobs list --kind ohlcv` → reads `cfg["jobs"]["ohlcv"]` and prints each key |
| Regular OHLCV config | `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml` | `jobs.ohlcv.nasdaq-100` block |
| Backfill config | `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv_backfill.yml` | `jobs.nasdaq-100` block (note: targets live directly under `jobs`, not `jobs.ohlcv`) |
| Schedule file | `infra/schedules.yml` | `ohlcv_daily` at `0 5 * * *`; `ohlcv_backfill_weekly` at `0 2 * * 0` |
| Primary OHLCV provider | `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/tradingview_provider.py` | `TradingViewOhlcvProvider.fetch_daily(exchange, symbol, ...)` — sends `EXCHANGE:SYMBOL` to tradingview-scraper WebSocket Streamer |
| Fallback OHLCV provider | `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/providers/yfinance_provider.py` | `YfinanceOhlcvProvider.fetch_daily(exchange, symbol, ...)` |
| Instrument resolution | `service.py` → `_resolve_instruments(repo, cfg, ticker)` | Calls `InstrumentQueryRepository.get_instruments_for_index(index_code=cfg["index_code"], country=cfg.get("country", "US"))` |
| Default exchange fallback | `service.py` line: `_DEFAULT_EXCHANGE = "NASDAQ"` | Applied when `cfg.get("default_exchange")` is absent |

### NASDAQ-100 `ohlcv.yml` Target Block (exact shape to mirror)

```yaml
jobs:
  ohlcv:
    nasdaq-100:
      code: ndx
      country: US
      type: index
      index_code: NDX
      timeframe: 1d
      window_days: 400
```

### NASDAQ-100 `ohlcv_backfill.yml` Target Block (exact shape to mirror)

```yaml
jobs:
  nasdaq-100:
    code: ndx
    country: US
    index_code: NDX
    timeframe: 1d
    default_exchange: NASDAQ
    default_chunk_days: 30
    window_days: 400
```

> **Critical structural difference:** In `ohlcv_backfill.yml`, targets sit directly under `jobs`, not under `jobs.ohlcv`. The `cli/main.py` dispatch reads `cfg.get("jobs", {})` (not `cfg["jobs"]["ohlcv_backfill"]`) for this job kind.

### Required Config Fields (from `service.py`)

```python
REQUIRED_CFG_FIELDS = ("code", "country", "index_code", "timeframe")
```

All four must be present in the BIST config entry or `run_ohlcv_ingestion` will raise `ValueError`.

### BIST Discovery Job Output (stored in DB, from Issue #41)

The `TradingViewBistDiscoveryProvider` (already implemented) calls:
```python
Query().set_markets('turkey').set_index('SYML:BIST;XU100').where(Column('is_primary') == True).limit(5000).get_scanner_data()
```
It stores instruments with: `ticker=<bare symbol>`, `country=TR`, `exchange=BIST`, `index_code=BIST` in `index_memberships`.

`_resolve_instruments` in the service calls `get_instruments_for_index(index_code='BIST', country='TR')`, which correctly returns exactly the XU100 subset stored by the discovery job. **No code changes to the service are needed.**

### TradingView Streamer Exchange Code Validation

`TradingViewOhlcvProvider.fetch_daily(exchange='BIST', symbol='THYAO')` will issue a WebSocket stream for `BIST:THYAO`. This is a valid TradingView symbol identifier. The `exchange` value `BIST` is already stored in the `instruments` table by the discovery job and flows through `_ingest_ticker → _fetch_with_fallback → tv_provider.fetch_daily(exchange=inst["exchange"])`.

---

## 1. Open Question Resolutions

All Open Questions from `plan.md` are resolved here. These decisions are **binding** for the Developer Agent.

| OQ | Decision | Rationale |
|----|----------|-----------|
| Q1 | **Resolved — confirmed.** `index_code=BIST` and `country=TR` are stored correctly by the discovery job. The OHLCV job's instrument resolver (`get_instruments_for_index(index_code='BIST', country='TR')`) will return the correct XU100 set. No DB verification blocker; proceed directly to Story 1. | User confirmed Q1. DB schema and discovery job code both confirm `index_code=BIST` is the stored value. |
| Q2 | **`window_days: 400`** — use the same value as NASDAQ-100. | Parity principle. 400 calendar days covers approximately 280 BIST trading days, which is ample. Borsa Istanbul data via tradingview-scraper is available for this window. |
| Q3 | **Cron time for `ohlcv_bist_daily`: `30 15 * * *` (UTC).** Borsa Istanbul trading ends at 18:10 Istanbul time. Turkey is UTC+3 year-round (no DST). 18:10 IST = 15:10 UTC. Schedule at 15:30 UTC ensures market has closed and data is settled. | User stated "just have something meaningful." 15:30 UTC is 30 minutes after Borsa Istanbul close. |
| Q4 | **Backfill parity is in scope.** Both `ohlcv_backfill.yml` entry and `ohlcv_bist_backfill_weekly` schedule are included. | Plan default assumption confirmed. Without backfill config, historical data population for BIST is impossible via CLI. |
| Q5 | **No live screener call in the OHLCV job itself.** The OHLCV job relies on instruments already stored in the DB by the discovery job. The discovery job already makes the `Query().set_index('SYML:BIST;XU100')` call and stores the result in `instruments` + `index_memberships`. The OHLCV job reads from this DB state via `_resolve_instruments`. **This is architecturally correct** — instrument discovery is the discovery job's responsibility; the OHLCV job's responsibility is candle fetching. A live screener call in the OHLCV job would duplicate discovery job concerns. `exchange=BIST` stored by the discovery job is the correct exchange code for the tradingview-scraper Streamer. See Tech Debt item T1 for future consideration. | User confirmed `.set_index('SYML:BIST;XU100')` is the correct filtering approach. That filter is already in the discovery provider. The OHLCV service's `_resolve_instruments` is equivalent because it reads what the discovery job stored. Modifying the service to add a live re-query would violate C2 and duplicate discovery concerns. |
| Q6 | **`default_chunk_days: 30`** — same as NASDAQ-100. | Parity principle. Safe default; can be tuned in follow-up if rate limiting is observed. |
| Q7 | **Include `type: index`** in the BIST `ohlcv.yml` entry. | Matches the NASDAQ-100 entry format exactly. The field is unused by the service but aids human readability. |

---

## 2. Updated Constraints

All constraints from `plan.md` carry forward. The following are additions or refinements from codebase investigation.

| # | Constraint |
|---|-----------|
| C1 | `OhlcvJob` class (`jobs/ohlcv_job.py`) MUST remain completely untouched. |
| C2 | `run_ohlcv_ingestion` service (`ohlcv/service.py`) MUST remain completely untouched. |
| C3 | The NASDAQ-100 entries in `config/ohlcv.yml`, `config/ohlcv_backfill.yml`, and `infra/schedules.yml` MUST remain completely untouched. |
| C4 | The target name key in `ohlcv.yml` MUST be `bist` (lowercase). This is used directly as the CLI `<target>` argument: `jobs run ohlcv bist`. |
| C5 | `index_code: BIST` (uppercase). Must match the value stored in `index_memberships.index_code` by the discovery job. |
| C6 | `country: TR` (uppercase). Must match the value stored in `instruments.country` by the discovery job. |
| C7 | All four `REQUIRED_CFG_FIELDS` — `code`, `country`, `index_code`, `timeframe` — MUST be present and non-empty in the bist config entry. |
| C8 | `default_exchange: BIST` MUST be explicitly present in both `ohlcv.yml` and `ohlcv_backfill.yml` for the bist target. Without it, the service falls back to `_DEFAULT_EXCHANGE = "NASDAQ"`, causing every BIST ticker to be streamed as `NASDAQ:<symbol>` — a silent data corruption. |
| C9 | `timeframe: 1d` (lowercase `d`). `TradingViewOhlcvProvider` hardcodes `TIMEFRAME = "1d"` internally; the config value is passed to `run_ohlcv_ingestion` where it is stored in `job_run_items` for audit but does NOT override the provider's constant. Nevertheless, the value must be `1d` for audit correctness and future compatibility. |
| C10 | Commit messages MUST follow `<prefix>(issue-46): <imperative description>`. Permitted prefixes: `feat`, `config`, `build`, `migration`, `fix`. |
| C11 | Each story maps to exactly ONE commit. |
| C12 | **Structural difference in backfill config:** `ohlcv_backfill.yml` places targets directly under `jobs`, NOT under `jobs.ohlcv`. The CLI dispatches: `cfg.get("jobs", {}).get(target)` (not `cfg["jobs"]["ohlcv_backfill"][target]`). |
| C13 | No new Python source files are to be created (no new provider, job class, or service). This issue is config-only plus one test file. |
| C14 | The BIST discovery job (Issue #41) is a **runtime prerequisite**. The developer must document this in any README notes but MUST NOT add code to enforce it at job startup. |
| C15 | `code: bist` in `ohlcv.yml` and `ohlcv_backfill.yml`. This value appears in the `job_run` audit log as part of the target identifier. It must be lowercase and consistent across both config files. Note: unlike the discovery factory which dispatches on `code`, the OHLCV service does NOT dispatch on `code` — the YAML key (e.g. `bist`) is the dispatch key in `cli/main.py`. |

---

## 3. Story Definitions (DETAILED)

---

### Story 1 — Add `bist` target to `config/ohlcv.yml`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml` | **Existing — append only** |

#### Changes Required

Open `config/ohlcv.yml`. The current file contains:

```yaml
jobs:
  ohlcv:
    nasdaq-100:
      code: ndx
      country: US
      type: index
      index_code: NDX
      timeframe: 1d
      window_days: 400
```

Append a second entry **at the same indentation level as `nasdaq-100`**, under `jobs.ohlcv`:

```yaml
    bist:
      code: bist
      country: TR
      type: index
      index_code: BIST
      timeframe: 1d
      window_days: 400
      default_exchange: BIST
```

**Mirror rule:** Every field present in `nasdaq-100` MUST have a counterpart in `bist`. The `default_exchange` field is added to `bist` even though it is absent from `nasdaq-100` because it is mandatory for non-NASDAQ markets (see C8).

**Field mapping from NASDAQ to BIST:**

| Field (nasdaq-100) | Value | Field (bist) | Value | Notes |
|--------------------|-------|--------------|-------|-------|
| `code` | `ndx` | `code` | `bist` | Audit label |
| `country` | `US` | `country` | `TR` | Must match `instruments.country` |
| `type` | `index` | `type` | `index` | Non-functional; for readability |
| `index_code` | `NDX` | `index_code` | `BIST` | Must match `index_memberships.index_code` |
| `timeframe` | `1d` | `timeframe` | `1d` | Identical |
| `window_days` | `400` | `window_days` | `400` | Identical |
| _(absent)_ | — | `default_exchange` | `BIST` | **Required for BIST; absent from NASDAQ entry because NASDAQ is the hardcoded default** |

#### Interfaces / Contracts

The `config/ohlcv.yml` dict is loaded by `load_config(config, default_filename="ohlcv.yml")` which returns the raw YAML dict. The CLI then calls:
```python
targets = cfg.get("jobs", {}).get("ohlcv", {})
target_cfg = targets.get("bist")
job = OhlcvJob.from_config(target_cfg, cfg)
job.run(ticker=ticker, from_date=from_date, to_date=to_date, limit_tickers=limit)
```

`OhlcvJob.run()` passes `self.target_cfg` as `cfg` to `run_ohlcv_ingestion`. The service reads:
- `cfg["code"]` → audit label
- `cfg["country"]` → passed to `_resolve_instruments`
- `cfg["index_code"]` → passed to `get_instruments_for_index`
- `cfg["timeframe"]` → stored in audit
- `cfg.get("window_days", 400)` → default candle window
- `cfg.get("default_exchange", "NASDAQ")` → exchange for tickers where `instruments.exchange IS NULL`

#### Acceptance Criteria

1. `python -m tayfin_ingestor_jobs jobs list --kind ohlcv` prints a line containing `bist` alongside `nasdaq-100`.
2. `load_config(default_filename="ohlcv.yml")["jobs"]["ohlcv"]["bist"]` is a dict.
3. All keys in `REQUIRED_CFG_FIELDS = ("code", "country", "index_code", "timeframe")` are present and non-empty in that dict.
4. `target_cfg["default_exchange"] == "BIST"`.
5. `target_cfg["country"] == "TR"` and `target_cfg["index_code"] == "BIST"`.
6. No existing line in `ohlcv.yml` is modified. The `nasdaq-100` block is identical to its state before this commit.

#### Exact Commit Message

```
config(issue-46): add bist ohlcv target to config/ohlcv.yml
```

---

### Story 2 — Add `bist` target to `config/ohlcv_backfill.yml`

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv_backfill.yml` | **Existing — append only** |

#### Changes Required

Open `config/ohlcv_backfill.yml`. The current file contains:

```yaml
jobs:
  nasdaq-100:
    code: ndx
    country: US
    index_code: NDX
    timeframe: 1d
    default_exchange: NASDAQ
    default_chunk_days: 30
    window_days: 400
```

Append a second entry **at the same indentation level as `nasdaq-100`**, directly under `jobs`:

```yaml
  bist:
    code: bist
    country: TR
    index_code: BIST
    timeframe: 1d
    default_exchange: BIST
    default_chunk_days: 30
    window_days: 400
```

**Critical structural note (C12):** Targets in `ohlcv_backfill.yml` live under `jobs.<target>`, NOT under `jobs.ohlcv.<target>`. The CLI reads: `cfg.get("jobs", {}).get("bist")`.

**Field mapping from NASDAQ to BIST:**

| Field (nasdaq-100) | Value | Field (bist) | Value |
|--------------------|-------|--------------|-------|
| `code` | `ndx` | `code` | `bist` |
| `country` | `US` | `country` | `TR` |
| `index_code` | `NDX` | `index_code` | `BIST` |
| `timeframe` | `1d` | `timeframe` | `1d` |
| `default_exchange` | `NASDAQ` | `default_exchange` | `BIST` |
| `default_chunk_days` | `30` | `default_chunk_days` | `30` |
| `window_days` | `400` | `window_days` | `400` |

#### Acceptance Criteria

1. `python -m tayfin_ingestor_jobs jobs list --kind ohlcv_backfill` prints a line containing `bist`.
2. `load_config(default_filename="ohlcv_backfill.yml")["jobs"]["bist"]` is a dict.
3. `target_cfg["default_exchange"] == "BIST"`.
4. All of `code`, `country`, `index_code`, `timeframe`, `default_exchange`, `default_chunk_days`, `window_days` are present and non-empty.
5. The `nasdaq-100` block is untouched.

#### Exact Commit Message

```
config(issue-46): add bist backfill target to config/ohlcv_backfill.yml
```

---

### Story 3 — Add BIST schedules to `infra/schedules.yml`

#### Files Touched

| File | Status |
|------|--------|
| `infra/schedules.yml` | **Existing — append only** |

#### Changes Required

Open `infra/schedules.yml`. The current file contains (relevant excerpts):

```yaml
ohlcv_daily:
  cron: "0 5 * * *"
  cmd: "python -m tayfin_ingestor_jobs jobs run ohlcv nasdaq-100 --config /app/config/ohlcv.yml"

ohlcv_backfill_weekly:
  cron: "0 2 * * 0"
  cmd: "python -m tayfin_ingestor_jobs jobs run ohlcv_backfill nasdaq-100 --config /app/config/ohlcv_backfill.yml"
```

Append two new schedule entries **after `ohlcv_backfill_weekly`**:

```yaml
ohlcv_bist_daily:
  cron: "30 15 * * *"
  # BIST OHLCV daily ingestion; runs after Borsa Istanbul close (18:10 IST = 15:10 UTC)
  cmd: "python -m tayfin_ingestor_jobs jobs run ohlcv bist --config /app/config/ohlcv.yml"

ohlcv_bist_backfill_weekly:
  cron: "30 2 * * 0"
  # BIST OHLCV weekly backfill; staggered 30 min after nasdaq-100 backfill
  cmd: "python -m tayfin_ingestor_jobs jobs run ohlcv_backfill bist --config /app/config/ohlcv_backfill.yml"
```

**Cron rationale:**
- `ohlcv_bist_daily` at `30 15 * * *`: Borsa Istanbul closes at 18:10 Istanbul time (UTC+3, no DST). 18:10 IST = 15:10 UTC. Schedule at 15:30 UTC gives 20-minute buffer post-close.
- `ohlcv_bist_backfill_weekly` at `30 2 * * 0`: `ohlcv_backfill_weekly` runs at `0 2 * * 0`. Stagger by 30 minutes to avoid concurrent Postgres write pressure.

**Command format rule (from NASDAQ reference):**
- Config path is always `/app/config/<filename>.yml` (container-mounted path, not relative).
- Target name must match the YAML key: `bist` (not `bist-100` or `xu100`).

#### Acceptance Criteria

1. `infra/schedules.yml` contains both `ohlcv_bist_daily` and `ohlcv_bist_backfill_weekly` as top-level keys.
2. `ohlcv_bist_daily.cmd` contains `jobs run ohlcv bist`.
3. `ohlcv_bist_backfill_weekly.cmd` contains `jobs run ohlcv_backfill bist`.
4. Both commands reference `--config /app/config/ohlcv*.yml` (container-mounted path). `ohlcv_bist_daily` → `/app/config/ohlcv.yml`; `ohlcv_bist_backfill_weekly` → `/app/config/ohlcv_backfill.yml`.
5. No existing schedule entry is modified.
6. YAML parses without error (`yaml.safe_load` on the file).

#### Exact Commit Message

```
config(issue-46): add bist ohlcv daily and backfill schedules to infra/schedules.yml
```

---

### Story 4 — Add test asserting BIST OHLCV config field completeness

#### Files Touched

| File | Status |
|------|--------|
| `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_bist_ohlcv_config.py` | **New file** |

#### Changes Required

Create a new pytest file at the path above. The test must:

1. Locate and load `config/ohlcv.yml` using the same `load_config` function used by the production code — specifically the package-local fallback path (`Path(__file__).resolve().parents[N] / "config" / "ohlcv.yml"`). This ensures the test validates the exact file the job uses.
2. Load `config/ohlcv_backfill.yml` using the same method.
3. Assert structural correctness of the `bist` entries in both files.

**Import pattern (mirror `test_ohlcv_backfill_failure_paths.py`):**
```python
from tayfin_ingestor_jobs.config.loader import load_config
```

**Test cases to implement (one test function per assertion group):**

| Test function | Assertion |
|---------------|-----------|
| `test_bist_ohlcv_target_exists` | `cfg["jobs"]["ohlcv"]["bist"]` is a non-None dict |
| `test_bist_ohlcv_required_fields` | All of `("code", "country", "index_code", "timeframe")` are present and non-empty strings |
| `test_bist_ohlcv_default_exchange` | `target["default_exchange"] == "BIST"` |
| `test_bist_ohlcv_country_and_index_code` | `target["country"] == "TR"` and `target["index_code"] == "BIST"` |
| `test_bist_ohlcv_timeframe` | `target["timeframe"] == "1d"` |
| `test_bist_backfill_target_exists` | `cfg_bf["jobs"]["bist"]` is a non-None dict |
| `test_bist_backfill_required_fields` | All of `("code", "country", "index_code", "timeframe", "default_exchange", "default_chunk_days", "window_days")` present |
| `test_bist_backfill_default_exchange` | `target_bf["default_exchange"] == "BIST"` |

**Loading pattern — no path argument, no DB, no network:**
```python
cfg = load_config(default_filename="ohlcv.yml")
cfg_bf = load_config(default_filename="ohlcv_backfill.yml")
```
`load_config` resolves to the package-local `config/` directory when no path is given and `TAYFIN_CONFIG_DIR` is unset. Tests must run offline without any environment variables set.

**Fixture pattern:** Use module-level fixtures or a `@pytest.fixture(scope="module")` for `cfg` and `cfg_bf` to avoid loading the same file repeatedly across tests.

#### Interfaces / Contracts

- Input: YAML files read by `load_config`
- Output: Assertions pass / fail
- No DB connection, no network calls, no environment variables required
- Must run with `pytest tests/test_bist_ohlcv_config.py -v` from the `tayfin-ingestor/tayfin-ingestor-jobs/` directory

#### Acceptance Criteria

1. `pytest tests/test_bist_ohlcv_config.py` exits with code 0 when Stories 1 and 2 are implemented.
2. If `bist` is removed from `ohlcv.yml`, `test_bist_ohlcv_target_exists` fails.
3. If `default_exchange` is removed from `ohlcv.yml` bist block, `test_bist_ohlcv_default_exchange` fails.
4. No real network calls are made. No DB connection is opened.
5. Test file has zero imports from job orchestration layers (`OhlcvJob`, `run_ohlcv_ingestion`, etc.) — only `load_config` and standard library.

#### Exact Commit Message

```
feat(issue-46): add test asserting bist ohlcv config target field completeness
```

---

## 4. Story Summary Table

| # | Story | Files | Commit |
|---|-------|-------|--------|
| 1 | Add `bist` to `ohlcv.yml` | `config/ohlcv.yml` (existing, append) | `config(issue-46): add bist ohlcv target to config/ohlcv.yml` |
| 2 | Add `bist` to `ohlcv_backfill.yml` | `config/ohlcv_backfill.yml` (existing, append) | `config(issue-46): add bist backfill target to config/ohlcv_backfill.yml` |
| 3 | Add BIST schedules to `schedules.yml` | `infra/schedules.yml` (existing, append) | `config(issue-46): add bist ohlcv daily and backfill schedules to infra/schedules.yml` |
| 4 | Add config completeness test | `tests/test_bist_ohlcv_config.py` (new) | `feat(issue-46): add test asserting bist ohlcv config target field completeness` |

---

## 5. Lead Dev Validation Steps

Perform these checks **before** handing to the Developer Agent, using only the files that exist in the repo right now (before implementation).

### Step 1 — Confirm BIST instruments are in DB (runtime pre-check)

```bash
# In a dev environment with the DB running:
SELECT COUNT(*) FROM tayfin_ingestor.index_memberships im
JOIN tayfin_ingestor.instruments i ON im.instrument_id = i.id
WHERE im.index_code = 'BIST' AND i.country = 'TR';
```
Expected: count ≥ 1 (ideally ~100 for XU100). If 0, the discovery job (Issue #41) has not been run. This is a **runtime blocker** but not an **implementation blocker** — stories 1–4 can be implemented regardless.

### Step 2 — Validate CLI routing for `ohlcv` kind

Trace `cli/main.py` `elif kind == "ohlcv"`:
- Reads `cfg.get("jobs", {}).get("ohlcv", {})` ✓
- Calls `targets.get(target)` where `target = "bist"` ✓
- Constructs `OhlcvJob.from_config(target_cfg, cfg)` ✓
- No hardcoded market routing exists → any target key in the YAML is valid ✓

### Step 3 — Validate CLI routing for `ohlcv_backfill` kind

Trace `cli/main.py` `elif kind == "ohlcv_backfill"`:
- Reads `cfg.get("jobs", {})` — note: no nested `ohlcv_backfill` key ✓
- Calls `targets.get("bist")` ✓
- Requires `bist` key directly under `jobs` in `ohlcv_backfill.yml` (C12 confirmed) ✓

### Step 4 — Confirm `_DEFAULT_EXCHANGE` fallback risk

In `service.py`:
```python
_DEFAULT_EXCHANGE = "NASDAQ"
default_exchange = cfg.get("default_exchange", _DEFAULT_EXCHANGE)
```
Without `default_exchange: BIST` in the config, every BIST ticker not found in `instruments.exchange` would be fetched as `NASDAQ:THYAO` — an invalid symbol. C8 is mandatory.

### Step 5 — Dry-run CLI invocation (after Stories 1–3)

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs
python -m tayfin_ingestor_jobs jobs list --kind ohlcv
# Expected output includes: bist: code=bist index_code=BIST timeframe=1d window_days=400

python -m tayfin_ingestor_jobs jobs list --kind ohlcv_backfill
# Expected output includes: bist: index_code=BIST default_exchange=BIST default_chunk_days=30
```

### Step 6 — Validate schedule YAML syntax

```bash
python -c "import yaml; yaml.safe_load(open('infra/schedules.yml'))"
# Must exit with code 0
```

### Step 7 — Run the config completeness test (after Story 4)

```bash
cd tayfin-ingestor/tayfin-ingestor-jobs
pytest tests/test_bist_ohlcv_config.py -v
# All 8 test functions must pass
```

---

## 6. Follow-up Tech Debt

| ID | Item | Risk | Suggested Future Action |
|----|------|------|-------------------------|
| T1 | **BIST instrument list is stale between discovery runs.** The OHLCV job uses instruments stored by the last discovery run. If an instrument is added or removed from XU100 between discovery runs, the OHLCV job will either miss new members or attempt to fetch delisted tickers. The Q5-preferred pattern (live screener call in OHLCV job to refresh the member list) would eliminate this. | Low-Medium. XU100 membership changes are infrequent (~annual rebalancing). | Future issue: add a `BistLiveInstrumentResolver` that calls `Query().set_index('SYML:BIST;XU100').get_scanner_data()` at OHLCV job start and intersects with DB instruments. Requires adding an `instruments_override` parameter to `run_ohlcv_ingestion` or a resolver injection point. |
| T2 | **`default_exchange` absent from NASDAQ-100 `ohlcv.yml` entry.** NASDAQ assumes the hardcoded default. This is fragile if the default ever changes. The BIST entry now has `default_exchange: BIST` explicitly, creating an asymmetry between the two entries. | Low. Default is hardcoded to `NASDAQ` and unlikely to change. | Add `default_exchange: NASDAQ` to the `nasdaq-100` ohlcv.yml entry for explicitness. Track as a separate housekeeping issue. |
| T3 | **`test_tradingview_bist_provider.py` patches `get_all_symbols` which no longer exists in the provider.** The discovery provider was updated to use `Query().get_scanner_data()` but the test still mocks the old `get_all_symbols` import. The tests pass trivially because the mock target resolves to nothing. | Medium. Test provides false confidence. | Fix the test to patch `tradingview_screener.Query` or use `unittest.mock.MagicMock` on the Query chain. Track as a separate bug fix issue. |
| T4 | **No end-to-end smoke test for BIST OHLCV pipeline.** The test added in Story 4 only validates config structure. There is no integration test that runs the full BIST OHLCV job against a real DB (even with a single ticker + `--limit 1`). | Medium. First real validation will be in production. | After discovery job has populated DB with BIST instruments, add an integration test mirroring `test_ohlcv_backfill_failure_paths.py` for the BIST target. Requires a running Postgres instance. |
| T5 | **No `ohlcv_bist_daily` schedule for indicator/screener pipelines.** Once BIST OHLCV data flows, downstream indicator and screener jobs (MA, VCP, etc.) will need BIST-specific targets. | Low for this issue; future blocker for BIST analytics. | Separate issues per bounded context: `tayfin-indicator` BIST target, `tayfin-screener` BIST target. |
