#!/usr/bin/env python3
"""List public Stockdex Ticker methods grouped by source prefix and write JSON inventory.

This script only uses reflection and does not call remote endpoints.
"""
import json
from stockdex import Ticker
import inspect
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    t = Ticker("AAPL")
    members = [m for m, _ in inspect.getmembers(type(t), predicate=inspect.isfunction) if not m.startswith("_")]
    grouped = defaultdict(list)
    prefixes = ["yahoo_api_", "yahoo_web_", "macrotrends_", "finviz_", "digrin_", "justetf_"]
    for m in sorted(members):
        matched = False
        for p in prefixes:
            if m.startswith(p):
                grouped[p].append(m)
                matched = True
                break
        if not matched:
            grouped["other"].append(m)

    out = {k: grouped[k] for k in sorted(grouped.keys())}
    p = OUT / "method_inventory.json"
    with p.open("w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print("Wrote", p)


if __name__ == "__main__":
    main()
