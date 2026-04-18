# Development Note: Switched from `get_all_symbols` to `Query().set_markets()`

**Date:** 2026-04-18  
**Branch:** `feature/issue-41-bist-discovery`  
**File affected:** `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/tradingview_bist.py`

---

## Context

The original implementation of `TradingViewBistDiscoveryProvider` used the top-level helper function `get_all_symbols(market='turkey')` from the `tradingview-screener` package. This function was available in version `2.5.0` and was validated in the spike (`tests/spikes/test_tradingview_screener_spike.py`) at the time the provider was written.

## What Changed and Why

When `tradingview-screener` was upgraded to `3.1.0` (tracked in `follow-up-technical-debt-2.md`), `get_all_symbols` was confirmed deprecated and removed from the public API. The package's new canonical approach is the `Query` builder class.

The provider was rewritten to use:

```python
raw_count, raw_df = (
    Query()
    .set_markets('turkey')
    .select('name')
    .limit(5000)
    .get_scanner_data()
)
```

### Key differences

| Aspect | `get_all_symbols` (v2.5.0) | `Query().set_markets()` (v3.1.0) |
|---|---|---|
| Return type | `list[str]` — plain list of `"BIST:SYMBOL"` strings | `(int, DataFrame)` — count + DataFrame with a `ticker` column |
| Market targeting | `market='turkey'` keyword argument | `.set_markets('turkey')` method chain |
| Availability | Deprecated / removed in 3.x | The supported API in 3.x |
| Flexibility | Single-purpose helper | Full query builder — supports `.where()`, `.order_by()`, `.limit()`, additional columns |

### Ticker extraction

Because the return type changed from a plain list to a DataFrame, the ticker extraction logic was updated accordingly:

```python
# Old (get_all_symbols — v2.5.0 era):
for symbol in raw_tickers:
    stripped = symbol.replace("BIST:", "", 1).strip().upper()

# New (Query — v3.1.0):
tickers_raw = raw_df['ticker'].tolist()
tickers = [t.replace('BIST:', '', 1).strip().upper() for t in tickers_raw if t.startswith('BIST:')]
```

The `ticker` column in the DataFrame always contains the full `EXCHANGE:SYMBOL` format (e.g., `BIST:THYAO`), so stripping the `BIST:` prefix produces the same clean ticker values as before.

## Outcome

- All ~630 Turkish tickers are still discovered correctly.
- The `startswith('BIST:')` guard ensures that any non-BIST rows (if TradingView ever returns mixed results for the turkey market) are safely ignored.
- The `limit(5000)` cap provides headroom well above the current ~630 symbol count.
- The `empty` check on the DataFrame replaces the previous incorrect `.all()` call on the DataFrame object.
