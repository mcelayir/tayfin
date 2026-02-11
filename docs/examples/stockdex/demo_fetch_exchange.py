#!/usr/bin/env python3
"""Demo script to fetch exchange for tickers using Stockdex.

This is a demo only - no DB, no job integration.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from stockdex import Ticker


def normalize_exchange(value):
    """Normalize exchange string: uppercase and strip spaces, map codes to names."""
    if isinstance(value, str):
        value = value.upper().strip()
        # Map common exchange codes to full names
        exchange_map = {
            "NMS": "NASDAQ",
            "NYQ": "NYSE",
            "ASE": "AMEX",
            "NCM": "NASDAQ",  # Sometimes used
        }
        return exchange_map.get(value, value)
    return str(value).upper().strip()


def find_exchange_for_ticker(ticker):
    """Find exchange for a single ticker using Stockdex."""
    t = Ticker(ticker)
    found = False
    result = {"ticker": ticker, "exchange": "NOT_FOUND", "source_method": "N/A", "field": "N/A"}

    # Try Yahoo API methods first
    yahoo_api_methods = ['yahoo_api_price']
    candidate_fields = ['exchangeName', 'exchange', 'fullExchangeName']

    for method_name in yahoo_api_methods:
        try:
            method = getattr(t, method_name)
            data = method()
            if isinstance(data, pd.DataFrame):
                for field in candidate_fields:
                    if field in data.columns and not data[field].empty:
                        exchange = data[field].iloc[0]  # Get from first row
                        exchange = normalize_exchange(exchange)
                        print(f"{ticker} | {exchange} | {method_name} | {field}")
                        result.update({
                            "exchange": exchange,
                            "source_method": method_name,
                            "field": field
                        })
                        found = True
                        break
            elif isinstance(data, dict):
                for field in candidate_fields:
                    if field in data and data[field]:
                        exchange = normalize_exchange(data[field])
                        print(f"{ticker} | {exchange} | {method_name} | {field}")
                        result.update({
                            "exchange": exchange,
                            "source_method": method_name,
                            "field": field
                        })
                        found = True
                        break
            if found:
                break
        except Exception as e:
            print(f"Error with {method_name} for {ticker}: {str(e)[:50]}...")
            continue

    # If not found, try Yahoo Web methods
    if not found:
        yahoo_web_methods = ['yahoo_web_financials_table']
        for method_name in yahoo_web_methods:
            try:
                method = getattr(t, method_name)
                data = method()
                if isinstance(data, pd.DataFrame):
                    for field in candidate_fields:
                        if field in data.columns and not data[field].empty:
                            exchange = data[field].iloc[0]
                            exchange = normalize_exchange(exchange)
                            print(f"{ticker} | {exchange} | {method_name} | {field}")
                            result.update({
                                "exchange": exchange,
                                "source_method": method_name,
                                "field": field
                            })
                            found = True
                            break
                elif isinstance(data, dict):
                    for field in candidate_fields:
                        if field in data and data[field]:
                            exchange = normalize_exchange(data[field])
                            print(f"{ticker} | {exchange} | {method_name} | {field}")
                            result.update({
                                "exchange": exchange,
                                "source_method": method_name,
                                "field": field
                            })
                            found = True
                            break
                if found:
                    break
            except Exception as e:
                print(f"Error with {method_name} for {ticker}: {str(e)[:50]}...")
                continue

    if not found:
        print(f"{ticker} | NOT_FOUND | N/A | N/A")

    return result


def main():
    parser = argparse.ArgumentParser(description="Demo: Fetch exchange for tickers using Stockdex")
    parser.add_argument(
        "--tickers",
        default="AAPL,MSFT,NVDA",
        help="Comma-separated list of tickers (default: AAPL,MSFT,NVDA)"
    )
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    results = []

    print("Ticker | Exchange | SourceMethod | FieldName")
    print("-" * 50)

    for ticker in tickers:
        try:
            result = find_exchange_for_ticker(ticker)
            results.append(result)
        except Exception as e:
            print(f"Failed to process {ticker}: {str(e)[:50]}...")
            results.append({
                "ticker": ticker,
                "exchange": "ERROR",
                "source_method": "N/A",
                "field": "N/A"
            })

    # Save to JSON
    out_dir = Path("docs/examples/stockdex/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "exchange_demo.json"

    with out_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {out_file}")


if __name__ == "__main__":
    main()