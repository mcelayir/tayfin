#!/usr/bin/env python3
"""Fetch daily OHLCV candles for a US stock via tradingview-scraper.

Uses the ``Streamer`` class from ``tradingview_scraper.symbols.stream`` in
export mode (``export_result=True``) to pull historical daily candles.

Usage:
    python docs/examples/tradingview_scraper/ohlcv/demo_fetch_daily_ohlcv.py
    python docs/examples/tradingview_scraper/ohlcv/demo_fetch_daily_ohlcv.py --exchange NASDAQ --symbol AAPL --limit 300
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Logging — suppress noisy library output, keep our messages visible
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.WARNING)
logging.getLogger("tradingview_scraper").setLevel(logging.WARNING)

DEFAULT_OUT = str(Path(__file__).resolve().parent.parent / "out" / "ohlcv")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Fetch daily OHLCV candles from TradingView")
parser.add_argument("--exchange", default="NASDAQ", help="TradingView exchange code (default: NASDAQ)")
parser.add_argument("--symbol", default="AAPL", help="Ticker symbol (default: AAPL)")
parser.add_argument("--timeframe", default="1d",
                    help="Timeframe key for Streamer (default: 1d). "
                         "Valid: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M")
parser.add_argument("--limit", type=int, default=300,
                    help="Number of candles to fetch (default: 300)")
parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_cookie() -> str | None:
    return os.environ.get("TRADINGVIEW_COOKIE")


def _build_streamer() -> "Streamer":
    from tradingview_scraper.symbols.stream import Streamer
    return Streamer(export_result=True, export_type="json")


def _fetch(streamer, exchange: str, symbol: str, timeframe: str, limit: int) -> list[dict]:
    """Fetch OHLCV candles; raise on auth/captcha errors."""
    try:
        result = streamer.stream(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            numb_price_candles=limit,
        )
    except Exception as exc:
        msg = str(exc).lower()
        if any(kw in msg for kw in ("captcha", "auth", "forbidden", "403", "unauthorized")):
            print(
                "\n*** Authentication / captcha error ***\n"
                "Set the TRADINGVIEW_COOKIE environment variable:\n"
                "    export TRADINGVIEW_COOKIE='<your cookie from browser DevTools>'\n"
                "See README.md in this folder for details.",
                file=sys.stderr,
            )
            sys.exit(2)
        raise

    ohlc = result.get("ohlc", [])
    if not ohlc:
        print(f"ERROR: No OHLCV data returned for {exchange}:{symbol} ({timeframe})", file=sys.stderr)
        sys.exit(3)
    return ohlc


def _to_dataframe(candles: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    df["as_of_date"] = df["timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    )
    df = df[["as_of_date", "open", "high", "low", "close", "volume"]]
    df = df.sort_values("as_of_date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parser.parse_args()

    print(f"Fetching {args.limit} daily candles for {args.exchange}:{args.symbol} (timeframe={args.timeframe}) ...")

    streamer = _build_streamer()
    candles = _fetch(streamer, args.exchange, args.symbol, args.timeframe, args.limit)
    df = _to_dataframe(candles)

    # Console output
    print(f"\n--- Results ---")
    print(f"Exchange:       {args.exchange}")
    print(f"Symbol format:  exchange='{args.exchange}', symbol='{args.symbol}' (separate params)")
    print(f"Timeframe:      {args.timeframe}")
    print(f"Shape:          {df.shape}")
    print(f"Date range:     {df['as_of_date'].min()} → {df['as_of_date'].max()}")
    print(f"\nHead(3):\n{df.head(3).to_string(index=False)}")
    print(f"\nTail(3):\n{df.tail(3).to_string(index=False)}")

    # Export
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = f"{args.exchange}_{args.symbol}_{args.timeframe}"

    csv_path = out_dir / f"ohlcv_{tag}.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nCSV  → {csv_path}")

    schema = {
        "exchange": args.exchange,
        "symbol": args.symbol,
        "symbol_format_used": f"exchange='{args.exchange}', symbol='{args.symbol}'",
        "timeframe": args.timeframe,
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "shape": list(df.shape),
        "min_date": df["as_of_date"].min(),
        "max_date": df["as_of_date"].max(),
    }
    schema_path = out_dir / f"ohlcv_{tag}_schema.json"
    with schema_path.open("w") as fh:
        json.dump(schema, fh, indent=2)
    print(f"JSON → {schema_path}")


if __name__ == "__main__":
    main()
