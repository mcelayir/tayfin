"""
Smoke test for the tradingview-screener library.

Runs a minimal live query and asserts structural invariants.
No values are compared — only schema and non-empty result.

Usage:
    python smoke_test.py

Exit code 0 = pass. Exit code 1 = fail.
"""

from tradingview_screener import Query, Column


def main() -> None:
    raw_count, df = (
        Query()
        .set_markets("turkey")
        .select("name", "close", "market_cap_basic")
        .where(Column("is_primary") == True)
        .limit(5)
        .get_scanner_data()
    )

    assert isinstance((raw_count, df), tuple), "Return value must be a tuple"
    assert raw_count > 0, f"raw_count must be > 0, got {raw_count}"
    assert len(df) > 0, "DataFrame must have at least one row"
    assert "ticker" in df.columns, "'ticker' column must be present"
    assert "name" in df.columns, "'name' column must be present"
    assert "close" in df.columns, "'close' column must be present"

    # ticker must be in EXCHANGE:SYMBOL format (Gotcha 1)
    sample_ticker = df["ticker"].iloc[0]
    assert ":" in sample_ticker, (
        f"'ticker' must be 'EXCHANGE:SYMBOL' format, got: {sample_ticker!r}"
    )

    print(f"smoke_test OK — {raw_count} rows available, {len(df)} returned")


if __name__ == "__main__":
    main()
