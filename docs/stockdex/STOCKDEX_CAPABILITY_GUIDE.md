# Stockdex Capability Guide

Overview
- Stockdex is a Python wrapper/collector for multiple public financial data sources (Yahoo, Macrotrends, Finviz, Digrin, JustETF, etc.).
- It exposes a `Ticker` abstraction with multiple data-source-specific methods named by prefix, e.g. `yahoo_api_*`, `yahoo_web_*`, `macrotrends_*`, `finviz_*`, `digrin_*`, `justetf_*`.

This guide is evidence-based: method names and availability are derived from the example introspection scripts in `docs/examples/stockdex/` and the generated inventory `docs/examples/stockdex/out/method_inventory.json`.

Capability matrix (summary)

The following table maps major data source prefixes to the kinds of datasets they typically expose. For exact method names and availability refer to `docs/examples/stockdex/out/method_inventory.json`.

| Data category | yahoo_api_* | yahoo_web_* | macrotrends_* | finviz_* | digrin_* | justetf_* |
|---|---:|---:|---:|---:|---:|---:|
| Price / historical price | available (yahoo_api_history, yahoo_api_price) | partial | not available | partial | not available | not available |
| Financial statements (BS/IS/CF) | available (yahoo_api_... statements) | available (yahoo_web_... tables) | partial | not available | partial | not available |
| Ratios / metrics | available | partial | partial | available | partial | not available |
| Company profile / summary | available | available | partial | available | partial | not available |
| ETF holdings / composition | limited | partial | partial | partial | not available | available (justetf_*) |

Rate-limits and stability notes
- Yahoo API methods (`yahoo_api_*`): generally reliable but subject to remote-side throttling; use retries/backoff. Some endpoints may change shape.
- Yahoo web scraping (`yahoo_web_*`): more fragile (HTML structure changes), likely to fail on parsing errors.
- Macrotrends / Finviz / Digrin: availability varies per symbol and may be slower; expect occasional missing pages.
- JustETF: intended for ETF data; availability limited to supported ETFs and regions.

How to run the examples
- Run the method inventory (no network required beyond importing Stockdex):

```bash
python docs/examples/stockdex/list_stockdex_methods.py
```

- Run a dump for Yahoo API methods for a symbol (example writes to `docs/examples/stockdex/out/AAPL/yahoo_api/`):

```bash
python docs/examples/stockdex/dump_yahoo_api_dataframes.py --ticker AAPL
```

- Run web scrapers:

```bash
python docs/examples/stockdex/dump_yahoo_web_dataframes.py --ticker AAPL
```

- Run other sources (macrotrends, finviz, digrin, justetf):

```bash
python docs/examples/stockdex/dump_other_sources_dataframes.py --ticker AAPL
```

Outputs
- The example scripts write to `docs/examples/stockdex/out/<TICKER>/<group>/` with deterministic file names:
  - `method_inventory.json` (method lists)
  - `schema_<method>.json` (columns, dtypes, shape, samples)
  - `data_<method>.csv` (exported data when non-empty)
  - `failures.json` (per-method failure records)

Recommended validation hooks
- Compare common metrics across `yahoo_api_*` and `yahoo_web_*` for the same symbol.
- Validate shapes (non-empty tables) and presence of expected columns for financial statements.
- Track per-method failure counts over time to detect source instability.

Notes
- This guide documents only methods and behaviors observed by the shipped examples; consult `docs/examples/stockdex/out/method_inventory.json` for the concrete method names present in the current environment.
