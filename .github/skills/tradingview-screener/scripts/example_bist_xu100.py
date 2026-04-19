"""
Example: BIST XU100 constituent listing.

Fetches all primary equity listings on BIST that are members of the XU100 index.
Prints the server-reported total count and the first 5 rows.

Usage:
    python example_bist_xu100.py

Requires: tradingview-screener >= 2.5.0
"""

from tradingview_screener import Query, Column


def main() -> None:
    raw_count, df = (
        Query()
        .set_markets("turkey")
        .set_index("SYML:BIST;XU100")
        .select(
            "name",
            "exchange",
            "market",
            "is_primary",
            "indexes",
            "close",
            "volume",
            "market_cap_basic",
        )
        .where(Column("is_primary") == True)
        .limit(5000)
        .get_scanner_data()
    )

    print(f"XU100 members (server count): {raw_count}")
    print(f"Rows returned: {len(df)}")
    print()
    print(df[["ticker", "name", "close", "market_cap_basic"]].head())


if __name__ == "__main__":
    main()
