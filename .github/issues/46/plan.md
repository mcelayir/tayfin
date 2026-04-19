# Plan: Issue #46 — Implement BIST OHLCV Ingestion Job

## Branch
`feature/issue-46-bist-ohlcv-job`

---

## 1. Overview

This issue delivers daily OHLCV candle ingestion for the BIST-100 (Borsa
Istanbul) market by registering a new target in the existing configuration
files consumed by the generic `OhlcvJob` orchestrator.

This is a **mirror implementation** of the NASDAQ-100 OHLCV job. The `OhlcvJob`
class (`tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/ohlcv_job.py`) and
the shared `run_ohlcv_ingestion` service
(`tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/service.py`) are fully
generic — they contain zero NASDAQ-specific code. Extending them to support
BIST requires only configuration additions and a new schedule entry.

**No new job class, provider class, or CLI routing code is to be written.**

The BIST-100 scope is already enforced by the BIST discovery job (Issue #41),
which filtered instruments to `SYML:BIST;XU100` before storing them with
`index_code=BIST` and `country=TR`. The OHLCV job inherits this scope by
resolving instruments via the same `index_code` + `country` pair.

---

## 2. Constraints & Conventions

| # | Constraint |
|---|-----------|
| C1 | The `OhlcvJob` class MUST remain completely untouched. |
| C2 | `run_ohlcv_ingestion` service MUST remain completely untouched. |
| C3 | The NASDAQ-100 entries in `config/ohlcv.yml`, `config/ohlcv_backfill.yml`, and `infra/schedules.yml` MUST remain completely untouched. |
| C4 | Market identifier MUST be `bist` (the target key in `ohlcv.yml`). This is consistent with the discovery config (`discovery.yml` key `bist`). |
| C5 | `index_code` in `ohlcv.yml` MUST be `BIST` — this must match the value stored by the BIST discovery job in the `index_memberships` table. |
| C6 | `country` in `ohlcv.yml` MUST be `TR` — this is the value set by the discovery provider and stored in the `instruments` table. |
| C7 | All four `REQUIRED_CFG_FIELDS` from `service.py` — `code`, `country`, `index_code`, `timeframe` — MUST be present in the `bist` config entry. |
| C8 | `default_exchange` MUST be explicitly set to `BIST` in `ohlcv.yml`. The service falls back to the hardcoded `_DEFAULT_EXCHANGE = "NASDAQ"` when the key is absent; without this field the OHLCV job would construct invalid TradingView stream requests for BIST symbols. |
| C9 | `timeframe` MUST be `1d` (lowercase). The `TradingViewOhlcvProvider` hardcodes `TIMEFRAME = "1d"` — uppercase `"1D"` silently defaults to 1-minute in `tradingview-scraper`. |
| C10 | Commit messages MUST follow the pattern `<prefix>(issue-46): <imperative description>`. Permitted prefixes: `feat`, `config`, `build`, `migration`, `fix`. |
| C11 | Each story maps to exactly ONE commit. |
| C12 | The OHLCV job operates against instruments already ingested by the discovery job. The BIST discovery job (Issue #41) MUST have been run before the BIST OHLCV job can succeed. This is a runtime dependency, not an implementation dependency. |
| C13 | The `tradingview-screener` library is **not** involved in OHLCV data fetching. The OHLCV provider stack uses `tradingview-scraper` (WebSocket streamer) as primary and `yfinance` as fallback. The `tradingview-screener` market identifier `turkey` is relevant only to confirm that `exchange=BIST` is the correct exchange code to pass to the TradingView stream API. |
| C14 | Scope is limited to BIST-100 (XU100). This scope is enforced by the discovery job; the OHLCV job inherits it automatically by querying `index_code=BIST`. |

---

## 3. Delivery Stories

### Repository Findings (Required for Story Execution)

| Finding | Value |
|---------|-------|
| OHLCV job class | `tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/jobs/ohlcv_job.py` → `OhlcvJob` |
| Shared service | `tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/ohlcv/service.py` → `run_ohlcv_ingestion()` |
| CLI entry point | `tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/cli/main.py` → `jobs run ohlcv <target>` |
| Regular OHLCV config | `tayfin-ingestor-jobs/config/ohlcv.yml` → `jobs.ohlcv.nasdaq-100` |
| Backfill config | `tayfin-ingestor-jobs/config/ohlcv_backfill.yml` → `jobs.nasdaq-100` |
| Schedule file | `infra/schedules.yml` → `ohlcv_daily` (05:00 UTC, nasdaq-100) |
| NASDAQ config fields | `code: ndx`, `country: US`, `type: index`, `index_code: NDX`, `timeframe: 1d`, `window_days: 400` |
| NASDAQ backfill extras | `default_exchange: NASDAQ`, `default_chunk_days: 30` |
| BIST instruments stored with | `index_code: BIST`, `country: TR`, `exchange: BIST` |
| REQUIRED_CFG_FIELDS (service.py) | `code`, `country`, `index_code`, `timeframe` |
| Default exchange fallback | `_DEFAULT_EXCHANGE = "NASDAQ"` (hardcoded in service.py — BIST must override) |

---

### Story Table

| # | Story | Prefix | Commit Message |
|---|-------|--------|----------------|
| 1 | Add `bist` target to `config/ohlcv.yml` | `config` | `config(issue-46): add bist ohlcv target to config/ohlcv.yml` |
| 2 | Add `bist` target to `config/ohlcv_backfill.yml` | `config` | `config(issue-46): add bist backfill target to config/ohlcv_backfill.yml` |
| 3 | Add `ohlcv_bist_daily` and `ohlcv_bist_backfill_weekly` schedules to `infra/schedules.yml` | `config` | `config(issue-46): add bist ohlcv daily and backfill schedules to infra/schedules.yml` |
| 4 | Add test asserting BIST OHLCV config target field completeness | `feat` | `feat(issue-46): add test asserting bist ohlcv config target field completeness` |

---

### Story Detail

#### Story 1 — Add `bist` target to `config/ohlcv.yml`

**Goal:** Register the BIST-100 OHLCV target so `jobs run ohlcv bist` resolves correctly.

**File:** `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml`

**Change:** Add a new `bist` key under `jobs.ohlcv` that mirrors the structure of `nasdaq-100`. All four `REQUIRED_CFG_FIELDS` must be present. `default_exchange` must be added explicitly (see C8). `window_days` should mirror the NASDAQ-100 value unless the open question on Turkish market windows is resolved differently.

**Acceptance criteria:**
- `jobs list --kind ohlcv` lists `bist` alongside `nasdaq-100`.
- The loaded config dict passes the `REQUIRED_CFG_FIELDS` validation in `service.py` without raising.
- `default_exchange` is `BIST` (not absent, not `NASDAQ`).
- No other lines in `ohlcv.yml` are modified.

---

#### Story 2 — Add `bist` target to `config/ohlcv_backfill.yml`

**Goal:** Enable `jobs run ohlcv_backfill bist` for historical backfill of BIST-100 candles, matching the NASDAQ-100 backfill configuration.

**File:** `tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv_backfill.yml`

**Note:** The backfill config structure differs from regular ohlcv — targets live directly under `jobs` (not `jobs.ohlcv`). See `cli/main.py`: `targets = cfg.get("jobs", {})` for `ohlcv_backfill`.

**Change:** Add a `bist` key under `jobs` mirroring `nasdaq-100`. Must include `code`, `country`, `index_code`, `timeframe`, `default_exchange: BIST`, `default_chunk_days`, `window_days`.

**Acceptance criteria:**
- `jobs list --kind ohlcv_backfill` lists `bist`.
- The loaded target dict resolves `default_exchange` to `BIST`.
- No other lines in `ohlcv_backfill.yml` are modified.

---

#### Story 3 — Add BIST schedules to `infra/schedules.yml`

**Goal:** Register automated cron triggers for BIST OHLCV ingestion that mirror the NASDAQ-100 schedule pattern.

**File:** `infra/schedules.yml`

**Change:** Add two new schedule entries:
1. `ohlcv_bist_daily` — daily candle ingestion, staggered after `ohlcv_daily` (currently 05:00 UTC). Exact cron offset is subject to open question Q3.
2. `ohlcv_bist_backfill_weekly` — weekly backfill, staggered after `ohlcv_backfill_weekly` (currently `0 2 * * 0`).

Both entries must use the pattern:
```
python -m tayfin_ingestor_jobs jobs run ohlcv bist --config /app/config/ohlcv.yml
python -m tayfin_ingestor_jobs jobs run ohlcv_backfill bist --config /app/config/ohlcv_backfill.yml
```

**Acceptance criteria:**
- `infra/schedules.yml` contains both `ohlcv_bist_daily` and `ohlcv_bist_backfill_weekly`.
- Command strings reference `bist` as the target name (not `nasdaq-100`).
- No existing schedule entries are modified.

---

#### Story 4 — Add test for BIST OHLCV config field completeness

**Goal:** Provide a fast, offline regression guard that fails immediately if the `bist` config entry is malformed or missing required fields.

**File:** `tayfin-ingestor/tayfin-ingestor-jobs/tests/test_bist_ohlcv_config.py`

**Change:** New pytest test file. Tests must:
1. Load `config/ohlcv.yml` via `load_config` (or direct YAML parse — no DB, no network).
2. Assert the `bist` key exists under `jobs.ohlcv`.
3. Assert all four `REQUIRED_CFG_FIELDS` (`code`, `country`, `index_code`, `timeframe`) are present and non-empty.
4. Assert `default_exchange` is present and equals `BIST`.
5. Assert `country` is `TR` and `index_code` is `BIST`.

**Acceptance criteria:**
- Test runs with `pytest tests/test_bist_ohlcv_config.py` without any DB or network access.
- Test fails if any required field is removed from `ohlcv.yml`.
- Test is analogous to the existing `test_ohlcv_backfill_failure_paths.py` in its import pattern.

---

## 4. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| Q1 | `index_code` consistency: the BIST discovery job stores instruments with `index_code=BIST` (from `discovery.yml`). Does the DB actually hold this value, or has it been overridden? The OHLCV job's `_resolve_instruments` calls `repo.get_instruments_for_index(index_code=index_code, country=country)` — if the stored value differs from `BIST`, the job will raise `ValueError: No instruments found`. | Blocks Story 1 if the stored `index_code` differs. | `@lead-dev` to verify against live DB before Story 1 commits. |
| Q2 | What `window_days` should BIST use? NASDAQ-100 uses 400 calendar days. Borsa Istanbul has fewer trading days per year (approx. 252), and data availability may differ. A different value (e.g. 365) might be more appropriate. | Affects Story 1 field value only. | `@lead-dev` to decide. Default assumption: `400` (parity with NASDAQ-100). |
| Q3 | What cron time for `ohlcv_bist_daily`? Borsa Istanbul closes at ~15:30 UTC (+3). The current `ohlcv_daily` runs at `0 5 * * *`. A time of ~`0 19 * * *` (after IST close) or early UTC morning next day (e.g. `0 3 * * *`) would both be valid patterns. | Affects Story 3 cron expression only. | `@lead-dev` to decide based on data freshness requirements. |
| Q4 | Is `ohlcv_bist_backfill_weekly` in scope for this issue? The NASDAQ-100 has `ohlcv_backfill_weekly`. Providing parity for BIST is natural, but the issue body (if it exists) may limit scope to the daily job only. | Affects Story 2 and Story 3 scope. If out of scope, Stories 2 and 3 reduce to one entry each. | `@lead-dev` to confirm scope. Default assumption: backfill parity is in scope. |
| Q5 | Does `TradingViewOhlcvProvider` correctly resolve BIST symbols? The provider sends `exchange=BIST, symbol=AKBNK` (for example) to the `tradingview-scraper` Streamer. This should produce the stream key `BIST:AKBNK`, which is a valid TradingView symbol. This must be confirmed with a live or spike test before Story 1 can be considered fully validated. | If BIST exchange code is wrong for the Streamer, all BIST tickers will return `PermanentProviderError` and fail over to yfinance. Not a blocker for config stories, but must be known before scheduling. | `@lead-dev` / developer to run a manual spike (`python -m tayfin_ingestor_jobs jobs run ohlcv bist --limit 1`) after Stories 1–3. |
| Q6 | What `default_chunk_days` should the BIST backfill use? NASDAQ-100 uses `30`. The same value is a safe default, but if BIST has denser data or stricter TradingView rate limits, a smaller value (e.g. `15`) might be warranted. | Affects Story 2 field value only. | `@lead-dev` to decide. Default assumption: `30` (parity). |
| Q7 | Should a `type` field be included in the BIST `ohlcv.yml` entry for documentation consistency? The NASDAQ-100 entry has `type: index`. The service does not use this field (`REQUIRED_CFG_FIELDS` does not include it). Including it maintains human readability of the config. | No functional impact. | Implementer can decide. Recommendation: include `type: index` for parity. |

---

## 5. Out of Scope

The following items are explicitly excluded from Issue #46:

| Item | Reason |
|------|--------|
| Modifications to `OhlcvJob` class | Already generic; BIST requires no code changes. |
| Modifications to `run_ohlcv_ingestion` service | Already generic; zero NASDAQ-specific logic. |
| Modifications to `cli/main.py` | Already routes any `ohlcv` kind dynamically from config; no new routing needed. |
| BIST discovery job changes | Implemented in Issue #41. Discovery is a prerequisite, not part of this issue. |
| `TradingViewOhlcvProvider` or `YfinanceOhlcvProvider` modifications | Providers are market-agnostic; they accept any exchange+symbol pair. |
| `tradingview-screener` library usage in OHLCV | That library is used only in discovery. OHLCV fetching uses `tradingview-scraper`. |
| New database migrations | The `ohlcv_daily` table already exists; the BIST instruments already have an `instrument_id`; no schema changes are required. |
| Changes to NASDAQ-100 schedules, config, or any NASDAQ artifacts | NASDAQ-100 MUST remain completely untouched. |
| Changes to `tayfin-indicator`, `tayfin-screener`, or `tayfin-app` | OHLCV ingestion is a `tayfin-ingestor` bounded-context concern only. |
| Indicator or screener jobs for BIST | Future issues; not in scope here. |
