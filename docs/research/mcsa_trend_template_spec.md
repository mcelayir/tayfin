# MCSA Trend Template — Research Specification

**Date:** 2026-03-08
**Author:** @pm-agent
**ADR:** [ADR-0001](../architecture/adr/ADR-0001-mcsa-trend-template.md)
**Epic:** [Issue #11](https://github.com/mcelayir/tayfin/issues/11)

---

## 1. Overview

This document specifies the Mark Minervini Stage Analysis (MCSA) Trend Template — the 8 criteria that determine whether a stock is in a Stage 2 uptrend. It serves as the **canonical reference** for the pure math module (Task 5) and the QA validation spec.

---

## 2. The 8 Criteria

### Criterion 1 — SMA-200 Trending Up and Price Above It

**Rule:** Price > SMA-200 AND SMA-200 is trending up for at least 1 month (~20 trading days).

**Implementation:**
```python
def criterion_1(close: float, sma_200: float, sma_200_slope: float) -> bool:
    return close > sma_200 and sma_200_slope > 0
```

**Inputs:**
- `close` — latest closing price
- `sma_200` — 200-day simple moving average (from `indicator_series`, key `sma`, params `{"window": 200}`)
- `sma_200_slope` — slope of SMA-200 over 20 bars (from `indicator_series`, key `sma_slope`, params `{"sma_window": 200, "slope_period": 20}`)

**Notes:**
- "Trending up for at least 1 month" is quantified as positive slope over 20 trading days.
- Slope formula: `(sma_today - sma_20_days_ago) / sma_20_days_ago`

---

### Criterion 2 — SMA-150 Above SMA-200

**Rule:** SMA-150 > SMA-200.

**Implementation:**
```python
def criterion_2(sma_150: float, sma_200: float) -> bool:
    return sma_150 > sma_200
```

**Inputs:**
- `sma_150` — from `indicator_series`, key `sma`, params `{"window": 150}`
- `sma_200` — from `indicator_series`, key `sma`, params `{"window": 200}`

---

### Criterion 3 — SMA-50 Above Both SMA-150 and SMA-200

**Rule:** SMA-50 > SMA-150 AND SMA-50 > SMA-200.

**Implementation:**
```python
def criterion_3(sma_50: float, sma_150: float, sma_200: float) -> bool:
    return sma_50 > sma_150 and sma_50 > sma_200
```

**Inputs:**
- `sma_50` — from `indicator_series`, key `sma`, params `{"window": 50}`
- `sma_150`, `sma_200` — as above

---

### Criterion 4 — Price Above SMA-50

**Rule:** Price > SMA-50.

**Implementation:**
```python
def criterion_4(close: float, sma_50: float) -> bool:
    return close > sma_50
```

---

### Criterion 5 — Price at Least 25% Above 52-Week Low

**Rule:** Price ≥ 1.25 × 52-week-low.

**Implementation:**
```python
def criterion_5(close: float, rolling_low_252: float) -> bool:
    return close >= 1.25 * rolling_low_252
```

**Inputs:**
- `rolling_low_252` — from `indicator_series`, key `rolling_low`, params `{"window": 252}`

**Notes:**
- 52 weeks ≈ 252 trading days.
- `rolling_low` is a new indicator (Task 2): `close.rolling(252).min()`

---

### Criterion 6 — Price Within 25% of 52-Week High

**Rule:** Price ≥ 0.75 × 52-week-high.

**Implementation:**
```python
def criterion_6(close: float, rolling_high_252: float) -> bool:
    return close >= 0.75 * rolling_high_252
```

**Inputs:**
- `rolling_high_252` — from `indicator_series`, key `rolling_high`, params `{"window": 252}`

---

### Criterion 7 — RS Ranking Above 70

**Rule:** Relative Strength ranking > 70 (i.e., stock is in the top 30th percentile of the screened universe).

**Implementation:**
```python
def criterion_7(rs_rank: float, threshold: float = 70.0) -> bool:
    return rs_rank > threshold
```

**RS Calculation (computed in screener, not stored as indicator):**

```python
def compute_rs_ranking(
    stock_returns: dict[str, float],  # ticker -> 6-month return
    benchmark_return: float,           # NDX 6-month return
) -> dict[str, float]:
    """
    Compute RS raw values and percentile rankings.
    
    RS_raw = (stock_6mo_return / benchmark_6mo_return) * 100
    RS_rank = percentile_rank(RS_raw) across all tickers
    """
    rs_raw = {
        ticker: (ret / benchmark_return) * 100 if benchmark_return != 0 else 0
        for ticker, ret in stock_returns.items()
    }
    sorted_values = sorted(rs_raw.values())
    n = len(sorted_values)
    return {
        ticker: (sorted_values.index(val) / n) * 100  # percentile
        for ticker, val in rs_raw.items()
    }
```

**Data source:**
- 6-month (≈126 trading days) OHLCV close prices from Ingestor API.
- Benchmark: NDX composite index.
- Return formula: `(close_today - close_126_days_ago) / close_126_days_ago`

---

### Criterion 8 — Price Above SMA-50 After Sound Base (PROXY)

**Rule (original):** Price is trading above SMA-50 after forming a sound base.

**Quantifiable proxy (HYPOTHESIS — requires validation):**
> "Price has been above SMA-50 for at least 5 of the last 10 trading days."

**Implementation (hypothesis):**
```python
def criterion_8(
    recent_closes: list[float],  # last 10 trading days, newest first
    recent_sma_50: list[float],  # last 10 SMA-50 values, newest first
) -> bool:
    days_above = sum(1 for c, s in zip(recent_closes, recent_sma_50) if c > s)
    return days_above >= 5
```

**Validation requirements:**
- [ ] Backtest the proxy against known Minervini Stage 2 stocks
- [ ] Compare with stricter variants (e.g., 7-of-10, 10-of-10)
- [ ] Document false positive / false negative characteristics
- [ ] @lead-dev must approve the final proxy before Task 5 implementation

**If hypothesis is rejected:** Propose an alternative proxy with the same validation requirements.

---

## 3. Data Requirements Summary

| Input | Source | API Endpoint | Indicator Key | Params |
|---|---|---|---|---|
| Close price | Ingestor API | `GET /ohlcv/range` | — | — |
| SMA-50 | Indicator API | `GET /indicators/index/latest` | `sma` | `{"window": 50}` |
| SMA-150 | Indicator API | `GET /indicators/index/latest` | `sma` | `{"window": 150}` |
| SMA-200 | Indicator API | `GET /indicators/index/latest` | `sma` | `{"window": 200}` |
| SMA-200 slope | Indicator API | `GET /indicators/index/latest` | `sma_slope` | `{"sma_window": 200, "slope_period": 20}` |
| Rolling High 252 | Indicator API | `GET /indicators/index/latest` | `rolling_high` | `{"window": 252}` |
| Rolling Low 252 | Indicator API | `GET /indicators/index/latest` | `rolling_low` | `{"window": 252}` |
| 6-mo close (RS) | Ingestor API | `GET /ohlcv/range` | — | 126-day range |
| NDX benchmark close | Ingestor API | `GET /ohlcv/range` | — | 126-day range |

---

## 4. Output Schema

The `evaluate_mcsa()` function returns an `McsaResult` dataclass:

```python
@dataclass
class McsaResult:
    ticker: str
    as_of_date: date
    mcsa_pass: bool           # True if ALL 8 criteria pass
    criteria_json: dict       # {"c1": true, "c2": false, ...}
    rs_rank: float            # 0-100 percentile
    criteria_count_pass: int  # 0-8, number of passing criteria
```

**`criteria_json` format:**
```json
{
    "c1_sma200_trending_up_and_price_above": true,
    "c2_sma150_above_sma200": true,
    "c3_sma50_above_sma150_and_sma200": false,
    "c4_price_above_sma50": true,
    "c5_price_25pct_above_52w_low": true,
    "c6_price_within_25pct_of_52w_high": false,
    "c7_rs_rank_above_70": true,
    "c8_price_above_sma50_sound_base": true
}
```

---

## 5. Determinism Guarantee

Running the MCSA screen job for the same `as_of_date` with the same indicator data MUST produce identical `criteria_json` output. The RS ranking is deterministic because:
- The screened universe is fixed (NDX-100 members for the given date).
- The 6-month return calculation uses fixed OHLCV data.
- Percentile ranking uses a deterministic sort (ties broken by ticker alphabetical order).

---

## 6. Simplifications & Limitations

| Simplification | Original Concept | Phase 0 Proxy | Impact |
|---|---|---|---|
| Criterion 8 | Discretionary "sound base" assessment | TBD — hypothesis: 5-of-10 days above SMA-50 | May produce false positives on choppy stocks |
| RS formula | Minervini's proprietary formula | 6-month return vs NDX | Approximation; true IBD RS uses a different weighting |
| Universe | Full market breadth | NDX-100 only | Limited to tech-heavy large caps |
| Benchmark | S&P 500 (traditional) | NDX itself | Relative to own universe, not broad market |
