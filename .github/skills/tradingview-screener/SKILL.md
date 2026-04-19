---
name: tradingview-screener
description: >
  Skill for querying financial market data using the tradingview-screener
  Python library. Covers the Query() API, field names, filter syntax,
  multi-market queries, index constituent retrieval, and fundamental
  screening. Load this skill whenever you need to write or debug a
  tradingview_screener Query: selecting columns, applying .where() filters,
  using .set_markets(), .set_index(), .order_by(), .limit(), or calling
  .get_scanner_data(). Includes a comprehensive field catalogue
  (references/fields.md), known gotchas (references/gotchas.md), and
  annotated usage examples (references/examples.md).
---

# Skill: tradingview-screener — Query API Reference

## When to load this skill

Load this skill whenever you are writing, reviewing, or debugging any Python
code that imports from `tradingview_screener`. This includes constructing
screener queries, selecting fields, applying filters, fetching index
constituents, or interpreting the returned `DataFrame`.

---

## Package identity

| Attribute | Value |
|-----------|-------|
| PyPI name | `tradingview-screener` |
| Import path | `from tradingview_screener import Query, Column` |
| `col` alias | `from tradingview_screener import col` — lowercase alias for `Column`; prefer `Column` in Tayfin code |
| Distinct from | `tradingview-scraper` (different PyPI package, already in `tayfin-ingestor-jobs/requirements.txt`) |
| Upstream docs | https://shner-elmo.github.io/TradingView-Screener/ |
| Fields reference | https://shner-elmo.github.io/TradingView-Screener/fields/stocks.html |

---

## `Query()` method chain

All methods return `self`, enabling fluent chaining. Call
`.get_scanner_data()` as the final method to execute the HTTP request.

### `.set_markets(*markets)`

Sets the market universe. Pass one or more market string identifiers.

```
.set_markets('turkey')               # single market
.set_markets('america', 'turkey')    # multi-market
```

Common market values: `'america'`, `'turkey'`, `'uk'`, `'germany'`,
`'india'`, `'china'`. Full list at the upstream fields page.

### `.set_index(index_id)`

Restricts results to constituents of a specific index.

```
.set_index('SYML:BIST;XU100')   # Borsa Istanbul XU100
.set_index('SYML:SP;SPX')       # S&P 500
```

The format is `SYML:<EXCHANGE>;<INDEX_CODE>`.

### `.select(*columns)`

Specifies which fields to fetch. Column names are case-sensitive string
literals. Look up exact names in `references/fields.md` before writing
any `.select()` call. The `ticker` column is always returned implicitly.

```
.select('name', 'close', 'volume', 'market_cap_basic')
```

### `.where(*conditions)`

Applies SQL-like row filters. Multiple conditions are ANDed automatically.
Each condition is built using `Column('field_name') <operator> value`.

```
.where(
    Column('is_primary') == True,
    Column('market_cap_basic') > 1_000_000_000,
)
```

Supported operators: `==`, `!=`, `<`, `<=`, `>`, `>=`, `.between(a, b)`,
`.isin([...])`. Use `.or_()` to combine conditions with OR logic.

### `.order_by(column, ascending=True)`

Sorts the result set. Combined with `.limit()`, this produces a true top-N.

```
.order_by('market_cap_basic', ascending=False)   # largest first
```

### `.offset(n)`

Skips the first N rows. Useful for pagination.

### `.limit(n)`

Caps the number of returned rows. Server default is 50. Use up to 200
without risk; values above 200 may trigger rate limiting. For index
constituent queries, use a high value (e.g. `5000`) to capture all members.

### `.get_scanner_data()`

Executes the HTTP request and returns a `(int, pd.DataFrame)` tuple.
No authentication is required for basic usage.

---

## Return value shape

```python
raw_count, df = query.get_scanner_data()
```

| Value | Type | Description |
|-------|------|-------------|
| `raw_count` | `int` | Total server-side match count before `.limit()` is applied |
| `df` | `pd.DataFrame` | Returned rows, capped at `.limit()` |

`raw_count > len(df)` is normal and expected whenever `.limit()` is set.

`df.columns` always includes `ticker` as the first column, plus every field
passed to `.select()`.

---

## Ticker format rule

Every value in `df['ticker']` is prefixed with the exchange identifier:

```
BIST:THYAO      NASDAQ:AAPL     NYSE:JPM
```

**Never** pass a bare symbol (e.g. `'THYAO'`) to `.where()` or any
downstream function that expects raw ticker values. Strip the prefix only
after retrieval:

```python
symbol = row['ticker'].replace('BIST:', '', 1)   # 'THYAO'
# or generically:
symbol = row['ticker'].split(':')[-1]
```

---

## End-to-end example

BIST XU100 index constituents — matching the current production query in
`tayfin-ingestor-jobs`:

```python
from tradingview_screener import Query, Column

raw_count, df = (
    Query()
    .set_markets('turkey')
    .set_index('SYML:BIST;XU100')
    .select('name', 'exchange', 'market', 'is_primary', 'indexes')
    .where(Column('is_primary') == True)
    .limit(5000)
    .get_scanner_data()
)
# raw_count: total matching symbols on server
# df: DataFrame with columns [ticker, name, exchange, market, is_primary, indexes]
# df['ticker'] values: 'BIST:THYAO', 'BIST:AKBNK', ...
```

---

## Reference files

Load these files on demand — do not load them preemptively.

| File | When to load |
|------|--------------|
| `references/fields.md` | Before writing any `.select()` or `.where()` call — look up exact column names here |
| `references/gotchas.md` | When results are unexpected, columns are missing, or duplicates appear |
| `references/examples.md` | When building a new query type not covered above |

---

## Scripts

`scripts/smoke_test.py` in this skill directory validates that
`tradingview_screener` is installed and live queries succeed. Run it as:

```
python scripts/smoke_test.py
```

Expected output: `smoke_test OK — N rows returned`
