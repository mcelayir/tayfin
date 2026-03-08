# ADR-0001: MCSA Trend Template Screener Architecture

- **Status:** Proposed
- **Date:** 2026-03-08
- **Author:** @lead-dev
- **Epic:** [Issue #11 — MCSA UI](https://github.com/mcelayir/tayfin/issues/11)

## Context

The Tayfin suite needs a new screener that evaluates Mark Minervini's Stage Analysis (MCSA) Trend Template — 8 criteria determining whether a stock is in a Stage 2 uptrend. This screener targets the NDX (Nasdaq 100) universe and must display results on a new dashboard UI.

The MCSA screener introduces several architectural questions not covered by the existing VCP screener precedent:

1. **New indicators needed:** `rolling_low(252)` and `sma_slope(200)` do not exist yet.
2. **Cross-ticker computation:** RS (Relative Strength) ranking is a percentile across the screened universe, not a per-ticker indicator.
3. **Qualitative criterion:** Criterion 8 ("sound base") has no canonical mathematical definition.
4. **UI layer:** No BFF or UI exists yet — framework choice must be made.
5. **Bulk data fetching:** The screener needs 6 indicator values per ticker × 100 tickers — API call patterns matter.

## Decision

### D1 — RS Ranking: Computed in the Screener (not stored as indicator)

RS ranking is computed at screening time inside `mcsa_screen_job`, not stored in `indicator_series`.

**Rationale:**
- RS rank is **relative to the screened universe**. The same stock would have a different rank if screened against BIST-100 vs NDX-100.
- `indicator_series` stores deterministic per-ticker computations. A cross-ticker percentile violates this semantic contract.
- The MCSA screen job already fetches all tickers in one pass — computing percentile ranking at that point is trivial.

**Formula (Decision D4):**
```
rs_raw = (stock_6mo_return / ndx_6mo_return) * 100
rs_rank = percentile_rank(rs_raw, across all tickers in screened universe)
```

- **Benchmark:** NDX composite index itself (not S&P 500).
- **Lookback:** 6-month (≈126 trading days) price return.
- **Data source:** OHLCV close prices fetched from Ingestor API for both individual stocks and NDX index.
- **Threshold:** Criterion 7 passes when `rs_rank > 70` (top 30th percentile).

### D2 — SMA Slope: Stored as Indicator

SMA-200 slope is stored in `indicator_series` as a precomputed indicator.

**Indicator key:** `sma_slope`
**Params:** `{"sma_window": 200, "slope_period": 20}`

**Rationale:**
- Follows the existing compute-once/serve-many pattern.
- The VCP screener already consumes `sma_50_slope` from the Indicator API — consistent pattern.
- Avoids the screener needing to fetch 20+ days of SMA-200 time-series data just to compute a slope (N+1 API explosion).

**Naming convention:**
- `sma_window` (not `window`) distinguishes which SMA's slope is being computed.
- `slope_period` specifies over how many bars the slope is measured.
- This disambiguates from SMA's own `params_json={"window": 200}`.

**Implementation constraint:**
The `SmaSlopeComputeJob` MUST read SMA-200 values from `IndicatorSeriesRepository` (direct DB read, same context — §1.1 allows this). It MUST NOT call the Indicator API. Calling the own API creates an unnecessary network hop and circular startup dependency.

**Dependency:** `ma_compute` must run before `sma_slope_compute` (SMA-200 data must exist).

### D3 — UI Framework: HTMX + Flask

The `tayfin-app` UI layer uses **HTMX + Flask/Jinja2** for Phase 0.

**Rationale:**
- Aligns with "local-first" philosophy — no Node.js build chain required.
- Avoids introducing a second runtime (Node.js) into the Docker Compose stack.
- HTMX provides dynamic partial updates (sorting, filtering, refresh) without a full SPA framework.
- Flask is already the approved API framework (TECH_STACK_RULES §6).
- Progressive enhancement: can be upgraded to a SPA later if needed.

**Stack:**
- `Flask` — app factory pattern (consistent with existing APIs)
- `Jinja2` — server-rendered templates
- `HTMX` — dynamic interactions (sorting, filtering, partial refreshes)
- `Typer` — CLI entry point (TECH_STACK_RULES §3 mandate)

**Alternatives rejected:**

| Alternative | Pros | Cons |
|---|---|---|
| React/Vue SPA | Rich interactivity | Introduces Node.js build chain, violates local-first simplicity |
| Flask + Jinja2 only (no HTMX) | Simplest possible | No dynamic interactions without full page reloads, poor UX for sorting/filtering |

### D5 — Criterion 8 Proxy: Deferred to Research Validation

Criterion 8 ("Price trading above SMA-50 after forming a sound base") is qualitative and has no canonical mathematical definition.

**Hypothesis to validate in research spec:**
> "Price has been above SMA-50 for at least 5 of the last 10 trading days."

This will be validated during implementation of `docs/research/mcsa_trend_template_spec.md`. The proxy must be:
- Deterministic and testable
- Documented with its simplification explicitly stated
- Approved by @lead-dev before Task 5 (pure math module) begins

If the hypothesis is rejected, an alternative proxy must be proposed before Task 5 proceeds.

## Alternatives Considered

### RS Ranking in Indicator Context
Store RS rank as an indicator in `indicator_series`.

| Aspect | Pros | Cons |
|---|---|---|
| Simplicity | Available via standard Indicator API | Violates semantic contract — RS is relative, not intrinsic |
| Reusability | Other screeners could consume it | Tied to a specific universe — ranks change per screening set |
| Consistency | Same API pattern for all data | Would need a "universe" parameter in `params_json`, making it a de facto screener |

**Rejected:** RS ranking is inherently a cross-ticker relative metric, not a per-ticker deterministic computation.

### SMA Slope Computed at Screening Time
Compute the SMA-200 slope inside the MCSA screen job instead of storing it as an indicator.

| Aspect | Pros | Cons |
|---|---|---|
| Freshness | Always computed from latest data | Requires fetching 20+ days of SMA-200 time-series per ticker |
| Simplicity | No new indicator job | 100 tickers × 20-day range = 100 API calls (N+1 explosion) |
| Pattern | — | Breaks compute-once/serve-many; VCP already uses stored slope |

**Rejected:** N+1 API explosion and inconsistency with VCP's existing `sma_50_slope` pattern.

### React SPA for UI
Full single-page application in `tayfin-ui/`.

**Rejected:** Introduces Node.js build chain (npm, webpack/vite), violates local-first simplicity for Phase 0. Can be revisited in later phases.

## Consequences

### Positive
- **Bounded context compliance:** All decisions respect context sovereignty. Indicators own computed per-ticker values; screeners own cross-ticker rankings.
- **Pattern consistency:** `rolling_low` and `sma_slope` follow identical patterns to existing indicator jobs. MCSA screen job follows VCP screen job patterns.
- **Efficient API usage:** 6 bulk `get_index_latest()` calls instead of 600 individual calls.
- **No new runtime dependencies:** HTMX + Flask avoids Node.js. No new Python libraries beyond what's already approved.
- **Incremental delivery:** 12 tasks ordered by dependency, parallelizable after ADR approval.

### Negative
- **Criterion 8 is approximate:** The quantifiable proxy is a simplification of Minervini's qualitative assessment. Must be clearly documented.
- **RS formula is simplified:** Using 6-month return vs NDX is one of many possible RS formulations. Documented as Phase 0 simplification.
- **HTMX learning curve:** Team may be less familiar with HTMX patterns compared to SPAs.

### Neutral
- **OHLCV dependency for RS:** The MCSA screen job needs close prices from the Ingestor API for the RS calculation. This is a standard cross-context API call, already supported by the existing `IngestorClient`.

## Implementation Guideline

### New Indicators (Tasks 2–3)

1. **`rolling_low(252)`** — Copy `RollingHighComputeJob` as template. Add `compute_rolling_low(close, window)` → `close.rolling(window).min()` to `indicator/compute.py`. Register as `"rolling_low_compute"` in `registry.py`.

2. **`sma_slope(200, 20)`** — Copy `RollingHighComputeJob` as template. Add `compute_sma_slope(sma_series, period)` to `indicator/compute.py`. Key difference: reads SMA-200 values from `IndicatorSeriesRepository` (same-context DB), NOT from API. Register as `"sma_slope_compute"` in `registry.py`.
   - `params_json`: `{"sma_window": 200, "slope_period": 20}`
   - Slope formula: `(sma_today - sma_N_days_ago) / sma_N_days_ago`

### Migration (Task 4)

```sql
CREATE TABLE tayfin_screener.mcsa_results (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id           uuid            NULL,
    ticker                  text            NOT NULL,
    as_of_date              date            NOT NULL,
    mcsa_pass               boolean         NOT NULL DEFAULT false,
    criteria_json           jsonb           NOT NULL DEFAULT '{}'::jsonb,
    rs_rank                 numeric         NOT NULL,
    criteria_count_pass     smallint        NOT NULL DEFAULT 0,
    created_at              timestamptz     NOT NULL DEFAULT now(),
    updated_at              timestamptz     NOT NULL DEFAULT now(),
    created_by_job_run_id   uuid            NOT NULL,
    updated_by_job_run_id   uuid            NULL,
    CONSTRAINT uq_mcsa_results UNIQUE (ticker, as_of_date)
);
```

### MCSA Screen Job — Bulk API Pattern (Task 7)

The job MUST fetch indicators using `get_index_latest()` (6 bulk calls):

```python
indicators_needed = [
    ("sma", {"window": 50}),
    ("sma", {"window": 150}),
    ("sma", {"window": 200}),
    ("rolling_high", {"window": 252}),
    ("rolling_low", {"window": 252}),
    ("sma_slope", {"sma_window": 200, "slope_period": 20}),
]
for indicator_key, params in indicators_needed:
    data = indicator_client.get_index_latest("NDX", indicator_key, params["window"])
    # build lookup dict: ticker -> value
```

Additionally, fetch OHLCV close prices from Ingestor API for RS calculation:
```python
# Fetch 6-month OHLCV for all NDX tickers
ohlcv_data = ingestor_client.get_ohlcv_range(ticker, from_date, to_date)
# Fetch NDX index OHLCV for benchmark return
ndx_ohlcv = ingestor_client.get_ohlcv_range("NDX", from_date, to_date)
```

### BFF + UI (Tasks 9a, 9b, 10)

- **9a:** Scaffold `tayfin-bff/` with Flask app factory + Typer CLI. httpx clients for Screener API and Indicator API.
- **9b:** `GET /api/mcsa/dashboard?index_code=NDX` endpoint. Calls `/mcsa/latest` from Screener API.
- **10:** Jinja2 template with HTMX. Table with sorting (`hx-get` with query params) and filtering.
