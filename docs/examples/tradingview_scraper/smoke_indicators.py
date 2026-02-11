#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import os
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default=os.environ.get("TV_SYMBOL", "BTCUSD"))
    p.add_argument("--exchange", default=os.environ.get("TV_EXCHANGE", "BINANCE"))
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--all", action="store_true")
    p.add_argument("--out", default="docs/examples/tradingview_scraper/out/")
    args = p.parse_args()

    out_dir = Path(args.out) / "indicators"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime(f"%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{args.exchange}_{args.symbol}_{args.timeframe}_{ts}.json"

    try:
        from tradingview_scraper.symbols.technicals import Indicators
    except Exception as e:
        print("tradingview_scraper Indicators import failed:", e, file=sys.stderr)
        sys.exit(2)

    try:
        ind = Indicators()
        # method signature: scrape(self, exchange: str = 'BITSTAMP', symbol: str = 'BTCUSD', timeframe: str = '1d', indicators: Optional[List[str]] = None, allIndicators: bool = False)
        if args.all:
            data = ind.scrape(exchange=args.exchange, symbol=args.symbol, timeframe=args.timeframe, allIndicators=True)
        else:
            # use a conservative list of supported indicators; STOCH.K may not be supported by installed package
            try:
                data = ind.scrape(exchange=args.exchange, symbol=args.symbol, timeframe=args.timeframe, indicators=["RSI", "STOCH.K"])
            except Exception:
                data = ind.scrape(exchange=args.exchange, symbol=args.symbol, timeframe=args.timeframe, indicators=["RSI"])
    except Exception as e:
        print("Indicators fetch failed:", e, file=sys.stderr)
        sys.exit(3)

    print(f"Indicators fetched for {args.exchange}:{args.symbol} {args.timeframe}")
    print(json.dumps(data if isinstance(data, dict) else (data[:5] if isinstance(data, list) else data), indent=2, default=str))

    with out_path.open("w") as fh:
        json.dump(data, fh, default=str, indent=2)


if __name__ == "__main__":
    main()
