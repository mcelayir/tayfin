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
    p.add_argument("--out", default="docs/examples/tradingview_scraper/out/")
    args = p.parse_args()

    out_dir = Path(args.out) / "news"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{args.symbol}_{ts}.json"

    try:
        from tradingview_scraper.symbols.news import NewsScraper
    except Exception as e:
        print("tradingview_scraper NewsScraper import failed:", e, file=sys.stderr)
        sys.exit(2)

    try:
        s = NewsScraper()
        # signature: scrape_headlines(self, symbol: str, exchange: str, ...)
        items = s.scrape_headlines(args.symbol, args.exchange)
    except Exception as e:
        print("News fetch failed:", e, file=sys.stderr)
        sys.exit(3)

    print(f"Fetched {len(items)} news items for {args.symbol}")
    if items:
        print(items[0])

    with out_path.open("w") as fh:
        json.dump(items, fh, default=str, indent=2)


if __name__ == "__main__":
    main()
