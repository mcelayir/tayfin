# Stockdex examples

Prerequisites
- Python 3.10+ (venv recommended)
- `pip install stockdex pandas` (the examples use `stockdex` and `pandas`)

How to run
- Generate a method inventory (no DB access required):

```bash
python docs/examples/stockdex/list_stockdex_methods.py
```

- Dump Yahoo API tables for a ticker:

```bash
python docs/examples/stockdex/dump_yahoo_api_dataframes.py --ticker AAPL
```

- Dump Yahoo web tables for a ticker:

```bash
python docs/examples/stockdex/dump_yahoo_web_dataframes.py --ticker AAPL
```

- Dump other sources (macrotrends/finviz/digrin/justetf):

```bash
python docs/examples/stockdex/dump_other_sources_dataframes.py --ticker AAPL
```

Outputs
- Files are written to `docs/examples/stockdex/out/<TICKER>/<group>/`.
- Each dataset attempted produces `schema_<method>.json` and optionally `data_<method>.csv`.
- Failures are recorded in `failures.json`.

Troubleshooting
- Stockdex may hit rate limits or fail if dependencies are missing; ensure `stockdex` is installed and network access is available.
- If a method repeatedly fails, inspect `failures.json` for the exception message.
