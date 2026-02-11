This folder contains TradingView streaming examples.

- `smoke_realtime_ohlcv.py` — uses `RealTimeData.get_ohlcv` to stream OHLCV messages and saves N messages to `out/`.
- `smoke_streamer_indicators.py` — uses `Streamer.stream` to request historical price candles and indicators; requires a websocket JWT token (env `TRADINGVIEW_WS_JWT` or `--jwt`).

Run the examples with the workspace virtualenv:

```bash
/home/muratcan/development/github/tayfin/.venv/bin/python docs/examples/tradingview_scraper/smoke_realtime_ohlcv.py --symbol BINANCE:BTCUSDT --count 5
/home/muratcan/development/github/tayfin/.venv/bin/python docs/examples/tradingview_scraper/smoke_streamer_indicators.py --exchange BINANCE --symbol BTCUSDT --timeframe 4h --numb_price_candles 100 --indicator_id "STD;RSI" --indicator_version 31.0 --jwt "$TRADINGVIEW_WS_JWT"
```
