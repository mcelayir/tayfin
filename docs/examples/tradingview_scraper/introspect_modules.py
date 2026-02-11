#!/usr/bin/env python3
from __future__ import annotations

import pkgutil
import inspect
import json
from pathlib import Path
from datetime import datetime
import tradingview_scraper


def main():
    out_dir = Path("docs/examples/tradingview_scraper/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"inventory_{ts}.json"

    inventory = {"root": tradingview_scraper.__name__, "modules": []}
    for module_info in pkgutil.iter_modules(tradingview_scraper.__path__):
        name = module_info.name
        entry = {"module": name, "classes": {}}
        try:
            mod = __import__(f"tradingview_scraper.{name}", fromlist=[name])
            for attr_name, attr in inspect.getmembers(mod, inspect.isclass):
                if attr.__module__.startswith("tradingview_scraper"):
                    methods = [m[0] for m in inspect.getmembers(attr, inspect.isfunction) if not m[0].startswith("_")]
                    entry["classes"][attr_name] = methods
        except Exception as e:
            entry["error"] = str(e)
        inventory["modules"].append(entry)

    with out_path.open("w") as fh:
        json.dump(inventory, fh, indent=2)
    print("Wrote", out_path)


if __name__ == "__main__":
    main()
