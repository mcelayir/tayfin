# TradingView OHLCV — Feasibility Demo

Proves we can fetch **daily OHLCV candles** for US stocks from TradingView
using the `tradingview-scraper` Python package.

## Prerequisites

```bash
pip install tradingview-scraper pandas
```

## Cookie / Authentication

Some TradingView endpoints may require a session cookie to bypass captcha.
If you hit auth errors, set the cookie:

```bash
# 1. Open https://www.tradingview.com/symbols/BTCUSD/ideas/ in your browser
# 2. Open DevTools (F12) → Network tab
# 3. Complete any captcha, then refresh
# 4. Copy the Cookie header from the first GET request
export TRADINGVIEW_COOKIE='<paste cookie value here>'
```

> **Never commit real cookie values.**

## Scripts

### 1. Introspect OHLCV Capability

Discovers which modules/classes in `tradingview-scraper` support OHLCV and
writes a structured inventory JSON.

```bash
python docs/examples/tradingview_scraper/ohlcv/introspect_ohlcv_capability.py
```

Output: `docs/examples/tradingview_scraper/out/ohlcv/inventory.json`

### 2. Fetch Daily OHLCV

```bash
# Default: NASDAQ AAPL, 300 daily candles
python docs/examples/tradingview_scraper/ohlcv/demo_fetch_daily_ohlcv.py

# Custom
python docs/examples/tradingview_scraper/ohlcv/demo_fetch_daily_ohlcv.py \
  --exchange NASDAQ --symbol MSFT --limit 200
```

**CLI arguments:**

| Arg           | Default   | Description                               |
|---------------|-----------|-------------------------------------------|
| `--exchange`  | `NASDAQ`  | TradingView exchange code                 |
| `--symbol`    | `AAPL`    | Ticker symbol (no exchange prefix)        |
| `--timeframe` | `1d`      | Candle timeframe (see table below)        |
| `--limit`     | `300`     | Number of candles                         |
| `--out`       | `out/ohlcv/` | Output directory                       |

**Valid timeframes:**

| Key   | Meaning   |
|-------|-----------|
| `1m`  | 1-minute  |
| `5m`  | 5-minute  |
| `15m` | 15-minute |
| `30m` | 30-minute |
| `1h`  | 1-hour    |
| `2h`  | 2-hour    |
| `4h`  | 4-hour    |
| `1d`  | **daily** |
| `1w`  | weekly    |
| `1M`  | monthly   |

## What Input Format Worked

The `Streamer` class from `tradingview_scraper.symbols.stream` takes
**separate** `exchange` and `symbol` parameters:

```python
from tradingview_scraper.symbols.stream import Streamer

streamer = Streamer(export_result=True, export_type="json")
result = streamer.stream(
    exchange="NASDAQ",    # exchange code
    symbol="AAPL",        # bare symbol (no prefix)
    timeframe="1d",       # lowercase '1d' for daily
    numb_price_candles=300,
)
ohlc = result["ohlc"]    # list of dicts with: index, timestamp, open, high, low, close, volume
```

- Symbol format: `exchange="NASDAQ"`, `symbol="AAPL"` (separate args)
- Internally combined as `NASDAQ:AAPL`
- Timeframe must be **lowercase** `1d` (uppercase `1D` falls through to 1-minute default)
- With `export_result=True` the method returns a dict instead of a streaming generator

## Output Files

All outputs go to `docs/examples/tradingview_scraper/out/ohlcv/` (git-ignored).

| File | Content |
|------|---------|
| `ohlcv_NASDAQ_AAPL_1d.csv` | Daily OHLCV as CSV |
| `ohlcv_NASDAQ_AAPL_1d_schema.json` | Columns, dtypes, shape, date range |
| `inventory.json` | Package introspection results |

## Troubleshooting

### Captcha / Auth error
Set `TRADINGVIEW_COOKIE` (see above). The script will print a clear message
and exit with code 2 if it detects an auth issue.

### Empty candles
- Verify the exchange code is correct (e.g., `NASDAQ` not `NMS` or `XNAS`).
- The symbol must exist on that exchange. Try a known pair first: `--exchange NASDAQ --symbol AAPL`.
- Check if TradingView is rate-limiting you (wait a minute and retry).

### Wrong exchange / symbol format
- Use TradingView's exchange codes, **not** MIC or Yahoo codes.
- Common mappings: `NASDAQ` for AAPL/MSFT/GOOG, `NYSE` for JPM/KO, `AMEX` for SPY.

### Rate limiting
- If you get empty results or errors after many consecutive calls, wait 30-60 seconds.
- Reduce `--limit` for initial testing.
- The WebSocket connection is short-lived; each call opens and closes one.
