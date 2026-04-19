"""
Example: Top 20 BIST stocks by USD market capitalisation.

Fetches the 20 largest BIST equity listings, sorted by market cap descending.
Prints the full DataFrame including P/E ratio and ROE.

Usage:
    python example_top_by_market_cap.py

Requires: tradingview-screener >= 2.5.0
"""

from tradingview_screener import Query, Column


def main() -> None:
    raw_count, df = (
        Query()
        .set_markets("turkey")
        .select(
            "name",
            "close",
            "market_cap_basic",
            "price_earnings_ttm",
            "return_on_equity",
            "total_revenue_ttm",
        )
        .where(Column("is_primary") == True)
        .where(Column("market_cap_basic") > 0)
        .order_by("market_cap_basic", ascending=False)
        .limit(20)
        .get_scanner_data()
    )

    print(f"Total BIST primary listings: {raw_count}")
    print(f"Top 20 by market cap (USD):")
    print()
    print(df[["ticker", "name", "market_cap_basic", "price_earnings_ttm", "return_on_equity"]].to_string())


if __name__ == "__main__":
    main()
