# Architecture Decision Record: MCSA Score Calculation Algorithm

## Status

**Accepted**

## Context

The Tayfin platform implements a multi-stage market analysis pipeline built on strict bounded contexts.

Pipeline structure:

- Ingestor → raw market data
- Indicator → technical indicators
- Screener → pattern detection and scoring

The Volatility Contraction Pattern (VCP) screener is implemented separately. The next scoring layer is MCSA (Minervini Chartist Scoring Algorithm), which ranks stocks using a deterministic weighted scoring model.

This document defines only the calculation algorithm for the MCSA score.

It does **not** define:

- schema design
- jobs
- APIs
- migrations
- context setup

Those belong to separate implementation tasks and architecture documents.

The goal here is to lock the scoring logic so implementation can remain consistent, explainable, and configurable.

---

## Decision

The project adopts MCSA v1 as a deterministic weighted scoring model composed of four signal groups:

1. Trend Structure
2. VCP / Base Quality
3. Volume Quality
4. Fundamentals

The final score range is:

- 0 to 100

The score is the weighted sum of the four components.

All major thresholds, weights, and lookback windows must be configurable.

No filenames or classes need to include the version name.

---

## Calculation Model

### Final Formula

```
mcsa_score = trend_score
           + vcp_component
           + volume_score
           + fundamental_score
```

Where each component is weighted and normalized according to configuration.

---

### Default Component Weights

Default weights for v1:

| Component       | Default Weight |
| --------------- | -------------- |
| Trend Structure | 30             |
| VCP Quality     | 35             |
| Volume Quality  | 15             |
| Fundamentals    | 20             |

**Total: 100**

These defaults must be configurable.

---

## Component Definitions

### 1. Trend Structure

**Purpose:**

- Ensure the stock is in a strong trend context

**Default signals:**

| Condition                                    | Default Points |
| -------------------------------------------- | -------------- |
| Price > SMA50                                | 8              |
| SMA50 > SMA150                              | 8              |
| SMA150 > SMA200                             | 8              |
| Price within 15% of rolling 52-week high     | 6              |

Trend score = sum of satisfied conditions.

**Configurable parameters:**

- `trend.price_above_sma50.points`
- `trend.sma50_above_sma150.points`
- `trend.sma150_above_sma200.points`
- `trend.near_52w_high.points`
- `trend.near_52w_high.max_distance_pct`

---

### 2. VCP / Base Quality

**Purpose:**

- Reflect pattern quality from the VCP screener

**Input:**

- `vcp_score`
- `pattern_detected`

**Default rule:**

```
vcp_component = normalized_vcp_score * 35
```

Where `normalized_vcp_score` is scaled to 0–1.

**Optional default cap:**

- If `pattern_detected = false`, cap this component at 15

**Configurable parameters:**

- `vcp.weight`
- `vcp.no_pattern_cap`
- `vcp.require_pattern_detected` (boolean, optional)

---

### 3. Volume Quality

**Purpose:**

- Measure supply contraction behavior during consolidation

**Default signals:**

| Condition                          | Default Points |
| ---------------------------------- | -------------- |
| Pullback volume below volume SMA   | 5              |
| Volume dry-up detected             | 5              |
| No abnormal selling spikes         | 5              |

Volume score = sum of satisfied conditions.

**Configurable parameters:**

- `volume.pullback_below_sma.points`
- `volume.dryup.points`
- `volume.no_heavy_selling.points`
- `volume.sma_window`
- `volume.dryup_threshold_pct`
- `volume.heavy_selling_threshold_pct`
- `volume.lookback_days`

---

### 4. Fundamentals

**Purpose:**

- Confirm business quality using already ingested fundamentals

**Default signals:**

| Condition                      | Default Points |
| ------------------------------ | -------------- |
| Revenue growth YoY > 15%      | 5              |
| Earnings growth YoY > 15%     | 5              |
| ROE > 15%                     | 4              |
| Net margin positive and strong | 3              |
| Debt/Equity below threshold   | 3              |

Fundamental score = sum of satisfied conditions.

**Configurable parameters:**

- `fundamentals.revenue_growth.min_pct`
- `fundamentals.revenue_growth.points`
- `fundamentals.earnings_growth.min_pct`
- `fundamentals.earnings_growth.points`
- `fundamentals.roe.min_pct`
- `fundamentals.roe.points`
- `fundamentals.net_margin.min_pct`
- `fundamentals.net_margin.points`
- `fundamentals.debt_equity.max_value`
- `fundamentals.debt_equity.points`

**Explicit non-decision:**

PE and PB are not part of the positive scoring model in v1.
They may be added later as soft penalties, but not in this version.

---

## Score Bands

Default interpretation bands:

| Score Range | Meaning          |
| ----------- | ---------------- |
| 85–100      | Strong candidate |
| 70–84       | Watchlist        |
| 50–69       | Neutral          |
| <50         | Weak             |

These should be configurable.

**Configurable parameters:**

- `bands.strong_min`
- `bands.watchlist_min`
- `bands.neutral_min`

---

## Time Range / Lookback Configuration

The algorithm depends on recent and historical values. These lookbacks must be configurable.

**Default assumptions:**

- Trend checks use latest indicator values on the scoring date
- Distance to rolling 52-week high uses the latest available rolling-high indicator
- Volume quality uses recent lookback windows
- VCP score comes from latest available VCP result on the scoring date
- Fundamentals use latest available fundamentals snapshot on the scoring date

**Configurable parameters:**

- `lookbacks.trend_days`
- `lookbacks.volume_days`
- `lookbacks.vcp_days`
- `lookbacks.fundamentals_days`

> **Note:** For v1, these may all effectively resolve to "latest available as of scoring date," but the configuration keys must exist so the algorithm is evolvable.

---

## Required Inputs to the Algorithm

The algorithm expects these inputs for each ticker at scoring time:

**Trend inputs:**

- latest price
- SMA50
- SMA150
- SMA200
- rolling 52-week high

**VCP inputs:**

- `vcp_score`
- `pattern_detected`

**Volume inputs:**

- recent volume behavior flags / measurements
- volume SMA

**Fundamental inputs:**

- `revenue_growth_yoy`
- `earnings_growth_yoy`
- `roe`
- `net_margin`
- `debt_equity`

If any required input is missing, the algorithm must either:

- score that component as zero, or
- mark the record as insufficient data,

according to configuration.

**Configurable behavior:**

- `missing_data.mode` = `zero` | `fail` | `partial`

**Recommended default:** `partial`

Meaning:

- compute what is possible
- record missing fields in evidence

---

## Evidence / Explainability Requirements

The algorithm must produce, alongside `mcsa_score`, a structured evidence object containing the raw values and rule outcomes used.

**Example:**

```json
{
  "trend": {
    "price_above_sma50": true,
    "sma50_above_sma150": true,
    "sma150_above_sma200": true,
    "distance_to_52w_high_pct": 0.08,
    "score": 30
  },
  "vcp": {
    "vcp_score": 82,
    "pattern_detected": true,
    "score": 28.7
  },
  "volume": {
    "pullback_below_sma": true,
    "volume_dryup": true,
    "no_heavy_selling": false,
    "score": 10
  },
  "fundamentals": {
    "revenue_growth_yoy": 0.23,
    "earnings_growth_yoy": 0.18,
    "roe": 0.19,
    "net_margin": 0.14,
    "debt_equity": 0.35,
    "score": 20
  },
  "total_score": 88.7,
  "band": "strong"
}
```

This is required so the score remains auditable.

---

## Default Configuration Shape

The scoring algorithm must be implemented so it can read a config structure similar to:

```yaml
mcsa:
  weights:
    trend: 30
    vcp: 35
    volume: 15
    fundamentals: 20

  trend:
    price_above_sma50:
      points: 8
    sma50_above_sma150:
      points: 8
    sma150_above_sma200:
      points: 8
    near_52w_high:
      points: 6
      max_distance_pct: 0.15

  vcp:
    no_pattern_cap: 15

  volume:
    sma_window: 50
    lookback_days: 20
    pullback_below_sma:
      points: 5
    dryup:
      points: 5
      threshold_pct: 0.5
    no_heavy_selling:
      points: 5
      heavy_selling_threshold_pct: 1.5

  fundamentals:
    revenue_growth:
      min_pct: 0.15
      points: 5
    earnings_growth:
      min_pct: 0.15
      points: 5
    roe:
      min_pct: 0.15
      points: 4
    net_margin:
      min_pct: 0.05
      points: 3
    debt_equity:
      max_value: 1.0
      points: 3

  bands:
    strong_min: 85
    watchlist_min: 70
    neutral_min: 50

  missing_data:
    mode: partial
```

The exact YAML file location is not defined here.

---

## Implementation Instructions (Algorithm Only)

### 1. Build the scoring logic as a pure calculation module

The algorithm implementation must be separable from:

- DB access
- API calls
- job orchestration
- Flask routes

Meaning:

- the scoring logic should accept normalized input values and config
- it should return:
  - component scores
  - total score
  - score band
  - evidence object

### 2. Make all weights configurable

Do not hardcode component weights in calculation logic.

Read them from configuration and validate that:

- they are numeric
- total weight equals 100 (or normalize explicitly if you choose to support non-100 sums)

**Recommended default:** require total = 100

### 3. Make all thresholds configurable

Do not hardcode:

- near 52-week high percentage
- growth thresholds
- debt/equity threshold
- volume dry-up threshold
- heavy selling threshold

All of these must come from configuration.

### 4. Make lookbacks configurable

Where time windows are needed for logic, use config values instead of hardcoded constants.

Examples:

- volume lookback days
- trend lookback assumptions
- acceptable recency of fundamentals/VCP inputs

### 5. Return structured evidence

The algorithm must always return a machine-readable evidence object alongside the score.

This is mandatory.

### 6. Support missing-data behavior by configuration

Implement configurable missing-data handling:

- `zero`
- `fail`
- `partial`

**Recommended behavior in v1:** `partial`

### 7. Keep algorithm deterministic

Same inputs + same config must always produce the same outputs.

No randomness. No hidden state.

---

## Consequences

**Benefits:**

- Explainable scoring
- Configurable weights and thresholds
- No hardcoded strategy assumptions in code
- Easier future calibration

**Trade-offs:**

- Requires disciplined config management
- Thresholds may still need tuning after observing real screener outputs

---

## Summary

MCSA v1 is a deterministic weighted score composed of trend, VCP quality, volume quality, and fundamentals.

This decision locks the calculation algorithm only and requires that weights, thresholds, and lookback assumptions be configurable from outside the scoring function.
