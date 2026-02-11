#!/usr/bin/env python3
"""Introspect the tradingview-scraper package for OHLCV-related capabilities.

Discovers modules, classes, and methods relevant to OHLCV / chart / candle
fetching inside the installed ``tradingview_scraper`` package and writes a
structured inventory to JSON.

Usage:
    python docs/examples/tradingview_scraper/ohlcv/introspect_ohlcv_capability.py
"""
from __future__ import annotations

import inspect
import json
import pkgutil
import sys
from pathlib import Path

KEYWORDS = {"chart", "candle", "ohlc", "history", "price", "stream", "technical"}

OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "ohlcv"


def _matches(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in KEYWORDS)


def main() -> None:
    try:
        import tradingview_scraper
    except ImportError:
        print("ERROR: tradingview-scraper is not installed. Run: pip install tradingview-scraper")
        sys.exit(1)

    version = getattr(tradingview_scraper, "__version__", "unknown")
    print(f"tradingview-scraper version: {version}")

    inventory: dict = {
        "package": "tradingview-scraper",
        "version": version,
        "relevant_modules": [],
        "relevant_classes": [],
    }

    # Walk all sub-modules
    for importer, modname, ispkg in pkgutil.walk_packages(
        tradingview_scraper.__path__,
        prefix="tradingview_scraper.",
    ):
        if not _matches(modname):
            continue

        entry: dict = {"module": modname, "classes": {}}
        try:
            mod = __import__(modname, fromlist=[modname.rsplit(".", 1)[-1]])
        except Exception as exc:
            entry["import_error"] = str(exc)
            inventory["relevant_modules"].append(entry)
            continue

        for cls_name, cls_obj in inspect.getmembers(mod, inspect.isclass):
            if not cls_obj.__module__.startswith("tradingview_scraper"):
                continue
            if not _matches(cls_name) and not _matches(modname):
                continue
            pub_methods = []
            for mname, _ in inspect.getmembers(cls_obj, predicate=inspect.isfunction):
                if not mname.startswith("_"):
                    pub_methods.append(mname)
            entry["classes"][cls_name] = {
                "methods": pub_methods,
                "init_signature": str(inspect.signature(cls_obj.__init__)),
            }
            inventory["relevant_classes"].append(
                {
                    "module": modname,
                    "class": cls_name,
                    "public_methods": pub_methods,
                }
            )

        inventory["relevant_modules"].append(entry)

    # Also explicitly check the Streamer class (primary OHLCV source)
    try:
        from tradingview_scraper.symbols.stream import Streamer

        sig = inspect.signature(Streamer.stream)
        streamer_info = {
            "module": "tradingview_scraper.symbols.stream",
            "class": "Streamer",
            "stream_signature": str(sig),
            "timeframe_map": {
                "1m": "1-minute",
                "5m": "5-minute",
                "15m": "15-minute",
                "30m": "30-minute",
                "1h": "1-hour",
                "2h": "2-hour",
                "4h": "4-hour",
                "1d": "daily",
                "1w": "weekly",
                "1M": "monthly",
            },
            "note": "Use export_result=True to get historical candles as dict; "
            "omit indicators for OHLCV-only mode.",
        }
        inventory["streamer_detail"] = streamer_info
        print(f"\nStreamer.stream signature: {sig}")
        print(f"Timeframe map: {json.dumps(streamer_info['timeframe_map'], indent=2)}")
    except Exception as exc:
        inventory["streamer_detail_error"] = str(exc)

    # Print summary
    print(f"\nRelevant modules found: {len(inventory['relevant_modules'])}")
    print(f"Relevant classes found: {len(inventory['relevant_classes'])}")
    for cls in inventory["relevant_classes"]:
        print(f"  {cls['module']}.{cls['class']}: {cls['public_methods']}")

    # Write JSON
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "inventory.json"
    with out_path.open("w") as fh:
        json.dump(inventory, fh, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
