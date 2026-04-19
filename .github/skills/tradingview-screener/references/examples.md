# TradingView Screener — Annotated Usage Examples

Four production-ready patterns covering the most common screener use-cases.
Each example is self-contained and runnable. Read `gotchas.md` first.

---

## Example A — BIST XU100 Constituent Listing

Fetches all primary equity listings on BIST that belong to the XU100 index.
This mirrors the production pattern in `docs/examples/tradingview_bist.py`.

```python
from tradingview_screener import Query, Column

# Build the query
raw_count, df = (
    Query()
    .set_markets('turkey')
    .set_index('SYML:BIST;XU100')  # filter to XU100 index members only
    .select(
        'name',
        'exchange',
        'market',
        'is_primary',
        'indexes',
        'close',
        'volume',
        'market_cap_basic',
    )
    .where(Column('is_primary') == True)  # deduplicate multi-listed symbols
    .limit(5000)                          # XU100 has ~100 members; 5000 is safe ceiling
    .get_scanner_data()
)

print(f"Server count: {raw_count}, Rows returned: {len(df)}")
print(df[['ticker', 'name', 'close', 'market_cap_basic']].head())
```

**Expected output shape:** ~100 rows (XU100 has exactly 100 constituents).
`ticker` column will be `BIST:THYAO`, `BIST:SASA`, etc.

---

## Example B — Top 20 BIST Stocks by Market Cap

Fetches the 20 largest BIST equities by USD market capitalisation. Common
starting point for fundamental screening.

```python
from tradingview_screener import Query, Column

raw_count, df = (
    Query()
    .set_markets('turkey')
    .select(
        'name',
        'close',
        'market_cap_basic',        # always USD
        'price_earnings_ttm',
        'return_on_equity',
        'total_revenue_ttm',
    )
    .where(Column('is_primary') == True)
    .where(Column('market_cap_basic') > 0)  # exclude NaN / zero cap
    .order_by('market_cap_basic', ascending=False)
    .limit(20)
    .get_scanner_data()
)

print(df[['ticker', 'name', 'market_cap_basic', 'price_earnings_ttm']])
```

**Notes:**
- `market_cap_basic` is USD regardless of exchange currency.
- `price_earnings_ttm` will be `NaN` for loss-making companies.
- The `.order_by()` sort is server-side; the returned DataFrame is already sorted.

---

## Example C — Fundamental Filter: Low P/E with Positive Net Income

Screens for undervalued BIST companies with a P/E below 10 and positive TTM
earnings. Useful for value screening.

```python
from tradingview_screener import Query, Column

raw_count, df = (
    Query()
    .set_markets('turkey')
    .select(
        'name',
        'close',
        'market_cap_basic',
        'price_earnings_ttm',
        'net_income_ttm',
        'return_on_equity',
        'debt_to_equity',
    )
    .where(Column('is_primary') == True)
    .where(Column('price_earnings_ttm') > 0)   # positive P/E only
    .where(Column('price_earnings_ttm') < 10)   # P/E below 10
    .where(Column('net_income_ttm') > 0)        # profitable (TTM)
    .order_by('price_earnings_ttm', ascending=True)
    .limit(100)
    .get_scanner_data()
)

print(f"Matches: {raw_count}")
print(df[['ticker', 'name', 'price_earnings_ttm', 'return_on_equity']].to_string())
```

**Notes:**
- Chaining multiple `.where()` calls applies AND logic.
- `price_earnings_ttm > 0` is essential: negative P/E (losses) is not the
  same as a "low" P/E and would contaminate results without this guard.

---

## Example D — Multi-Market Query: USA + Turkey

Demonstrates querying across multiple markets in a single call. Useful for
cross-market comparison of technical indicators.

```python
from tradingview_screener import Query, Column

raw_count, df = (
    Query()
    .set_markets('america', 'turkey')   # multiple markets in one call
    .select(
        'name',
        'exchange',
        'market',
        'close',
        'RSI',
        'MACD.macd',
        'MACD.signal',
        'SMA50',
        'SMA200',
        'market_cap_basic',
    )
    .where(Column('is_primary') == True)
    .where(Column('RSI') < 35)          # oversold (RSI below 35)
    .where(Column('market_cap_basic') > 1_000_000_000)  # > $1B cap
    .order_by('RSI', ascending=True)
    .limit(50)
    .get_scanner_data()
)

print(f"Oversold large-caps across USA+Turkey: {raw_count} matches")
print(df[['ticker', 'market', 'close', 'RSI']].head(10))
```

**Notes:**
- When combining markets, the `market` column identifies which market each
  row belongs to (`america`, `turkey`).
- `MACD.macd` uses dot notation — the `.` is part of the field name, not a
  Python attribute accessor.
- `RSI` is the default 14-period RSI on the daily timeframe.
- For intraday RSI: use `'RSI|60'` (hourly) or `'RSI|15'` (15-min) in `.select()`.
