# Exchange Demo README

## Purpose
This demo script explores which Stockdex datasets provide reliable exchange information for US tickers. It tries Yahoo API methods first, then Yahoo Web methods, and extracts exchange data from the response.

## How to Run

### Default tickers (AAPL, MSFT, NVDA)
```bash
python docs/examples/stockdex/demo_fetch_exchange.py
```

### Custom tickers
```bash
python docs/examples/stockdex/demo_fetch_exchange.py --tickers AAPL,TSLA,GOOGL
```

## Output
- Console output shows a table with Ticker | Exchange | SourceMethod | FieldName
- JSON file is written to `docs/examples/stockdex/out/exchange_demo.json`

## Notes
This is exploration to learn which Stockdex datasets provide exchange information. The script uses only real Stockdex APIs and handles errors gracefully.