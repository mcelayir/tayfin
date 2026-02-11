#!/usr/bin/env python3
"""Example: use Streamer to stream OHLC + indicators (requires websocket JWT for indicators).

Usage:
  python smoke_streamer_indicators.py --exchange BINANCE --symbol BTCUSDT --timeframe 4h \
      --numb_price_candles 100 --indicator_id "STD;RSI" --indicator_version 31.0 \
      --jwt $TRADINGVIEW_WS_JWT

If no --jwt is provided, the script will look for environment variable TRADINGVIEW_WS_JWT and exit if missing.
"""
import argparse
import json
import os
from datetime import datetime

try:
    from tradingview_scraper.symbols.stream import Streamer
except Exception as e:
    raise SystemExit(f"Failed to import tradingview_scraper.symbols.stream.Streamer: {e}")

parser = argparse.ArgumentParser()
parser.add_argument("--exchange", default="BINANCE")
parser.add_argument("--symbol", default="BTCUSDT")
parser.add_argument("--timeframe", default="4h")
parser.add_argument("--numb_price_candles", type=int, default=100)
parser.add_argument("--indicator_id", default="STD;RSI")
parser.add_argument("--indicator_version", default="31.0")
parser.add_argument("--jwt", default=os.environ.get("TRADINGVIEW_WS_JWT"))
parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "out"))
args = parser.parse_args()

if not args.jwt:
    raise SystemExit("This example requires a TradingView websocket JWT token. Provide via --jwt or TRADINGVIEW_WS_JWT env var.")

os.makedirs(args.out_dir, exist_ok=True)

streamer = Streamer(export_result=False, export_type='json', websocket_jwt_token=args.jwt)
print(f"Starting streamer for {args.exchange}:{args.symbol} timeframe={args.timeframe} ...")

collected = None
try:
    gen = streamer.stream(
        exchange=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        numb_price_candles=args.numb_price_candles,
        indicator_id=args.indicator_id,
        indicator_version=str(args.indicator_version),
    )
    # consume the first payload (historical export + first realtime update)
    collected = next(gen)
    print("Received payload (truncated):")
    print(json.dumps(collected if isinstance(collected, dict) else {"payload_type": str(type(collected))}, indent=2, default=str)[:800])
except StopIteration:
    print("Streamer generator closed without data")
except Exception as e:
    print("Streamer error:", e)
finally:
    try:
        # attempt a graceful shutdown if available
        if hasattr(streamer, 'stop'):
            streamer.stop()
    except Exception:
        pass

if collected is not None:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(args.out_dir, f"streamer_{args.exchange}_{args.symbol}_{ts}.json")
    with open(out_path, 'w') as f:
        json.dump({"exchange": args.exchange, "symbol": args.symbol, "payload": collected, "ts": ts}, f, indent=2, default=str)
    print("WROTE", out_path)
else:
    print("No payload saved.")
