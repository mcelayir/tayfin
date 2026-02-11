#!/usr/bin/env python3
"""Simple smoke script for tradingview_scraper Ideas.

Writes JSON to out/ideas/<symbol>_<ts>.json and prints a compact summary.
"""
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
    p.add_argument("--out", default="docs/examples/tradingview_scraper/out/")
    args = p.parse_args()

    out_dir = Path(args.out) / "ideas"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{args.symbol}_{ts}.json"

    try:
        from tradingview_scraper.symbols.ideas import Ideas
    except Exception as e:
        print("tradingview_scraper Ideas import failed:", e, file=sys.stderr)
        print("If this is a captcha/block, set TRADINGVIEW_COOKIE and retry.")
        sys.exit(2)

    try:
        scraper = Ideas()
        # signature: scrape_ideas(self, symbol: str, page: int, sort: str)
        items = scraper.scrape_ideas(args.symbol, 1, "latest")
    except Exception as e:
        print("Ideas fetch failed:", e, file=sys.stderr)
        sys.exit(3)

    # redact long bodies for console
    for i in items[:2]:
        if "body" in i and isinstance(i["body"], str) and len(i["body"]) > 400:
            i["body"] = i["body"][:400] + "...[truncated]"

    print(f"Fetched {len(items)} ideas for {args.symbol}")
    if items:
        print(json.dumps(items[:2], indent=2, default=str))

    with out_path.open("w") as fh:
        json.dump(items, fh, default=str, indent=2)


if __name__ == "__main__":
    main()
