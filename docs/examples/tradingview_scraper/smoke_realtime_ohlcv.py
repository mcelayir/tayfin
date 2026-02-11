#!/usr/bin/env python3
"""Simple example: stream OHLCV using RealTimeData.get_ohlcv and collect N messages.

Usage:
  python smoke_realtime_ohlcv.py --symbol BINANCE:BTCUSDT --count 5
"""
import argparse
import json
import os
from datetime import datetime

try:
    from tradingview_scraper.symbols.stream import RealTimeData
except Exception as e:
    raise SystemExit(f"Failed to import tradingview_scraper.symbols.stream.RealTimeData: {e}")

parser = argparse.ArgumentParser()
parser.add_argument("--symbol", default="BINANCE:BTCUSDT")
parser.add_argument("--count", type=int, default=5, help="How many OHLC messages to collect then exit")
parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "out"))
args = parser.parse_args()

os.makedirs(args.out_dir, exist_ok=True)
rt = RealTimeData()
print(f"Connecting and collecting up to {args.count} OHLC messages for {args.symbol}...")
collected = []
try:
    gen = rt.get_ohlcv(exchange_symbol=args.symbol)
    for i, item in enumerate(gen):
        # item is expected to be a dict-like OHLCV update
        print(f"[{i+1}] got message:\n", json.dumps(item, indent=2, default=str))
        collected.append(item)
        if i + 1 >= args.count:
            break
except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print("Stream error:", e)

# write output
ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
out_path = os.path.join(args.out_dir, f"realtime_ohlcv_{args.symbol.replace(':','_')}_{ts}.json")
with open(out_path, "w") as f:
    json.dump({"symbol": args.symbol, "collected": collected, "ts": ts}, f, indent=2, default=str)
print("WROTE", out_path)
