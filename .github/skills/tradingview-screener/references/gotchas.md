# TradingView Screener — Gotchas & Edge Cases

Mandatory reading before writing any production query. Every item here was
discovered from real API behaviour; none are obvious from the library's README.

---

## Gotcha 1 — The `ticker` column always uses `EXCHANGE:SYMBOL` format

Every row in the returned DataFrame has a `ticker` column formatted as
`EXCHANGE:SYMBOL` (e.g. `BIST:THYAO`, `NASDAQ:AAPL`). This is NOT the same
as TradingView's display symbol.

**Impact:**

- You cannot pass `ticker` values directly to other APIs that expect bare
  symbols without stripping the prefix first.
- When doing join operations between the screener result and your own database,
  apply `df['ticker'].str.split(':').str[1]` to extract the bare symbol.

**Example:**

```python
# Safe extraction of bare symbol
count, df = Query().set_markets('turkey').select('name').limit(5).get_scanner_data()
bare_symbols = df['ticker'].str.split(':').str[1]  # ['THYAO', 'SASA', ...]
```

---

## Gotcha 2 — Always filter `is_primary == True` for BIST and multi-listing markets

Many symbols are listed on multiple exchanges and appear multiple times in the
screener results. Without the `is_primary` filter you will get duplicate rows
for the same company — one per listing.

The `is_primary` column is a **boolean**. Use `Column('is_primary') == True`
(not a string `"True"`).

**Example:**

```python
from tradingview_screener import Query, Column

count, df = (
    Query()
    .set_markets('turkey')
    .where(Column('is_primary') == True)  # REQUIRED — eliminates duplicates
    .select('name', 'exchange', 'close')
    .limit(5000)
    .get_scanner_data()
)
```

---

## Gotcha 3 — `market_cap_basic` is in USD, not local currency, and can be NaN

The `market_cap_basic` field is always denominated in **USD** regardless of
the exchange currency. For BIST stocks priced in TRY, the value is already
USD-converted (using TradingView's internal FX rate at query time).

Additionally, `market_cap_basic` returns `NaN` for symbols where TradingView
has not populated this field (common for thinly-traded instruments,
certificates, and some ETFs). **Never assume this column is fully populated.**

**Safe pattern:**

```python
count, df = Query().set_markets('turkey').select('name', 'market_cap_basic').get_scanner_data()
df_with_cap = df.dropna(subset=['market_cap_basic'])   # exclude NaN rows
```

---

## Gotcha 4 — `raw_count` ≠ `len(df)` when using `.limit()`

`get_scanner_data()` returns a `tuple[int, pd.DataFrame]`. The first element
(`raw_count`) is the **total number of matching symbols** on the server BEFORE
the `.limit()` is applied. `len(df)` is the number of rows actually returned
(≤ limit).

**Example:**

```python
raw_count, df = Query().set_markets('turkey').limit(10).get_scanner_data()
# raw_count might be 540 (all BIST symbols)
# len(df) will be 10
```

Always use `raw_count` to check how many results the query actually matched,
and increase `.limit()` if you need all of them.

---

## Gotcha 5 — No authentication is required, but requests are rate-limited

The library makes un-authenticated HTTP calls to TradingView's screener API.
No API key or login token is needed. However:

- TradingView **rate-limits** this endpoint. If you hammer it in a tight loop,
  expect `HTTP 429` or silent timeouts.
- In production, add a sleep between batch calls:

```python
import time
time.sleep(1.5)  # minimum safe inter-call delay
```
- Do **not** run `.get_scanner_data()` inside a per-row loop. Batch the entire
  screener call with a sufficiently large `.limit()` and process in-memory.

---

## Gotcha 6 — `.get_scanner_data()` is a network call; it is non-deterministic

Every call to `.get_scanner_data()` sends an HTTP POST to TradingView's
servers. This means:

- **Results are live.** Price, volume, and indicator values change between
  calls made seconds apart.
- **Order is non-deterministic.** The same query can return rows in different
  order on successive calls. Always sort the DataFrame explicitly:

```python
df = df.sort_values('market_cap_basic', ascending=False)
```
- **Tests that compare exact values will be flaky.** In tests, assert
  structural properties only (column presence, dtypes, `len > 0`) — never
  assert specific price or indicator values.
- Jobs that write to a database must use a `job_run_id` to tie each screener
  snapshot to a single run.

---

## Quick Reference

| Gotcha | Rule |
|--------|------|
| `ticker` format | Always `EXCHANGE:SYMBOL` — strip prefix for joins |
| Duplicates | Add `.where(Column('is_primary') == True)` for BIST/multi-list markets |
| `market_cap_basic` | USD-denominated, may be `NaN` — use `dropna()` defensively |
| `raw_count` vs `len(df)` | `raw_count` = server total; `len(df)` = returned rows (≤ limit) |
| Rate limiting | Add `time.sleep(1.5)` between back-to-back calls |
| Non-determinism | Sort explicitly; assert structure only in tests; link writes to `job_run_id` |
