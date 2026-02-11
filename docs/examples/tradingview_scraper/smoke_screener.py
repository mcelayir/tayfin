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
    p.add_argument("--market", default=os.environ.get("TV_MARKET", "america"))
    p.add_argument("--out", default="docs/examples/tradingview_scraper/out/")
    args = p.parse_args()

    out_dir = Path(args.out) / "screener"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{args.market}_{ts}.json"

    # Try a few possible screener import names; be defensive
    screener = None
    tried = []
    try:
        from tradingview_scraper.symbols.screener import Screener
    except Exception as e:
        print("tradingview_scraper Screener import failed:", e, file=sys.stderr)
        sys.exit(2)

    try:
        s = Screener()
        # method signature: screen(self, market: str = 'america', filters: Optional[List[Dict[str, Any]]] = None, columns: Optional[List[str]] = None, sort_by: Optional[str] = None, sort_order: str = 'desc', limit: int = 50)
        rows = s.screen(market=args.market, limit=50)
    except Exception as e:
        print("Screener query failed:", e, file=sys.stderr)
        sys.exit(3)

    # rows may be list or dict depending on library implementation
    try:
        count = len(rows)
    except Exception:
        count = 1
    print(f"Screener returned {count} rows for market={args.market}")
    if isinstance(rows, list):
        print(json.dumps(rows[:10], indent=2, default=str))
    else:
        print(json.dumps(rows, indent=2, default=str))

    with out_path.open("w") as fh:
        json.dump(rows, fh, default=str, indent=2)


if __name__ == "__main__":
    main()
