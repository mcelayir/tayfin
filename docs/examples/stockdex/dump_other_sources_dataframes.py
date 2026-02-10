#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import inspect
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pandas as pd
from stockdex import Ticker
from _utils import write_schema_and_data


def call_method(ticker_obj, method_name):
    # Conservative handling: most justetf_* methods only apply to ETFs.
    # Try to detect ETF-like attributes; if we can't confirm ETF, skip to avoid heavy failures.
    if method_name.startswith("justetf_"):
        is_etf = False
        candidates = ("security_type", "type", "instrument_type", "asset_type", "securityType", "is_etf")
        for a in candidates:
            try:
                v = getattr(ticker_obj, a)
            except Exception:
                continue
            # If attribute is callable (e.g., is_etf()), try to call it safely
            try:
                if callable(v):
                    try:
                        r = v()
                    except Exception:
                        r = None
                    v = r
            except Exception:
                pass
            if isinstance(v, str) and v.lower() == "etf":
                is_etf = True
                break
            if isinstance(v, bool) and v:
                is_etf = True
                break
        if not is_etf:
            return {"skipped": True, "reason": "requires ETF - skipped for non-ETF instrument"}

    try:
        fn = getattr(ticker_obj, method_name)
    except Exception as e:
        msg = str(e)
        if "Wrong security type" in msg or "Wrong security type" in repr(e):
            return {"skipped": True, "reason": "Wrong security type - skipped for non-ETF instrument"}
        raise

    if not callable(fn):
        return fn
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return {"skipped": True, "reason": "cannot inspect signature"}
    required = []
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if param.default is inspect._empty:
            required.append(name)
    if required:
        return {"skipped": True, "reason": f"requires args: {required}"}
    try:
        return fn()
    except Exception as e:
        msg = str(e)
        # Treat JustETF wrong-security-type errors as skips (ETF-only methods)
        if "Wrong security type" in msg or "Wrong security type" in repr(e):
            cleaned = "Wrong security type - skipped for non-ETF instrument"
            return {"skipped": True, "reason": cleaned}
        # Propagate other exceptions to be treated as real failures
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", default="AAPL")
    p.add_argument("--out", default="docs/examples/stockdex/out")
    p.add_argument("--format", choices=["csv", "json", "both"], default="both")
    args = p.parse_args()

    outroot = Path(args.out) / args.ticker / "other_sources"
    outroot.mkdir(parents=True, exist_ok=True)

    t = Ticker(args.ticker)
    prefixes = ["macrotrends_", "finviz_", "digrin_", "justetf_"]
    methods = []
    for pfx in prefixes:
        methods.extend([m for m in dir(t) if m.startswith(pfx)])
    methods = sorted(methods)

    failures = []
    for m in methods:
        try:
            val = call_method(t, m)
        except Exception as e:
            failures.append({"method": m, "error": str(e)})
            print(f"{m}: FAILED: {e}")
            continue

        # Handle skipped results returned from call_method
        if isinstance(val, dict) and val.get("skipped"):
            schema = {"name": m, "type": "skipped", "reason": val.get("reason")}
            with (outroot / f"schema_{m}.json").open("w") as f:
                json.dump(schema, f, indent=2)
            print(f"{m}: SKIPPED: {val.get('reason')}")
            continue

        if isinstance(val, pd.DataFrame):
            write_schema_and_data(outroot, m, val, args.format)
            print(f"{m}: wrote schema and data (shape={val.shape})")
        else:
            schema = {"name": m, "type": type(val).__name__}
            with (outroot / f"schema_{m}.json").open("w") as f:
                json.dump(schema, f, indent=2)
            print(f"{m}: returned {type(val).__name__}")

    if failures:
        with (outroot / "failures.json").open("w") as f:
            json.dump(failures, f, indent=2)
        print("Some methods failed; see failures.json")


if __name__ == "__main__":
    main()
