# tradingview_scraper examples

Prerequisites
- Python 3.10+ and a virtual environment.
- Install the package used by examples:

  pip install tradingview-scraper

Setting cookie (if captcha required)
- If you encounter captchas or empty results, set `TRADINGVIEW_COOKIE` in your shell:

  export TRADINGVIEW_COOKIE="<your_tradingview_cookie_here>"

Running examples
- From the repository root, run (examples write to `docs/examples/tradingview_scraper/out/` by default):

  python docs/examples/tradingview_scraper/smoke_ideas.py --symbol BTCUSD
  python docs/examples/tradingview_scraper/smoke_indicators.py --symbol BTCUSD --timeframe 1d
  python docs/examples/tradingview_scraper/smoke_news.py --symbol BTCUSD
  python docs/examples/tradingview_scraper/smoke_screener.py --market america
  python docs/examples/tradingview_scraper/introspect_modules.py

Outputs
- All outputs are stored under `docs/examples/tradingview_scraper/out/` and are ignored by git.

Realtime streaming examples
- smoke_realtime_ohlcv.py — streams OHLCV using RealTimeData.get_ohlcv and saves a configurable
  number of messages to the `out/` folder.
- smoke_streamer_indicators.py — streams OHLC plus indicators using Streamer; this example
  requests historical price candles and indicator history and requires a TradingView websocket JWT
  token (provide via the TRADINGVIEW_WS_JWT environment variable or the `--jwt` flag).

Run the realtime examples (use your virtualenv python if needed):

```bash
python docs/examples/tradingview_scraper/smoke_realtime_ohlcv.py --symbol BINANCE:BTCUSDT --count 5
python docs/examples/tradingview_scraper/smoke_streamer_indicators.py \
  --exchange BINANCE --symbol BTCUSDT --timeframe 4h --numb_price_candles 100 \
  --indicator_id "STD;RSI" --indicator_version 31.0 --jwt "$TRADINGVIEW_WS_JWT"
```

Notes
- Both examples require the `tradingview-scraper` package to be installed in your environment:

```bash
pip install tradingview-scraper
```

- If you encounter captchas or empty results, set TRADINGVIEW_COOKIE in your shell:

```bash
export TRADINGVIEW_COOKIE="<your_tradingview_cookie_here>"
```

