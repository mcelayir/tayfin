#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import pandas as pd
from stockdex import Ticker
from docs.examples.stockdex._utils import write_schema_and_data


def call_method(ticker_obj, method_name):
    fn = getattr(ticker_obj, method_name)
    return fn()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", default="AAPL")
    p.add_argument("--out", default="docs/examples/stockdex/out")
    p.add_argument("--format", choices=["csv", "json", "both"], default="both")
    args = p.parse_args()

    outroot = Path(args.out) / args.ticker / "yahoo_web"
    outroot.mkdir(parents=True, exist_ok=True)

    t = Ticker(args.ticker)
    methods = [m for m in dir(t) if m.startswith("yahoo_web_")]
    methods = sorted(methods)

    failures = []
    for m in methods:
        try:
            val = call_method(t, m)
            if isinstance(val, pd.DataFrame):
                write_schema_and_data(outroot, m, val, args.format)
                print(f"{m}: wrote schema and data (shape={val.shape})")
            else:
                schema = {"name": m, "type": type(val).__name__}
                with (outroot / f"schema_{m}.json").open("w") as f:
                    json.dump(schema, f, indent=2)
                print(f"{m}: returned {type(val).__name__}")
        except Exception as e:
            failures.append({"method": m, "error": str(e)})
            print(f"{m}: FAILED: {e}")

    if failures:
        with (outroot / "failures.json").open("w") as f:
            json.dump(failures, f, indent=2)
        print("Some methods failed; see failures.json")


if __name__ == "__main__":
    main()
