# stockdex fundamentals fetcher for NASDAQ stocks
# Usage: from stockdex_fundamentals import fetch_stockdex_fundamentals
from stockdex import Ticker

import pandas as pd
import json

def fetch_stockdex_fundamentals(ticker: str) -> dict:
    """
    Fetches key fundamentals (PE, PB, ROE, net margin, debt/equity) for a given NASDAQ ticker using stockdex.
    Returns a dict with keys: pe_ratio, pb_ratio, roe, net_margin, debt_equity, rev_growth_qoq, earnings_growth_qoq
    """
    # Remove exchange prefix if present (e.g., NASDAQ:TLT -> TLT)
    symbol = ticker.split(":", 1)[1] if ":" in ticker else ticker
    t = Ticker(ticker=symbol)
    fin = t.yahoo_api_financials(frequency="quarterly")
    inc = t.yahoo_api_income_statement(frequency="quarterly")
    bal = t.yahoo_api_balance_sheet(frequency="quarterly")

    def get_latest(df, field):
        """Get the latest (most recent) value for a field or sum of fields from a DataFrame."""
        if isinstance(field, list):
            vals = [df[f].iloc[0] for f in field if f in df.columns and pd.notnull(df[f].iloc[0])]
            return sum(vals) if vals else None
        if field in df.columns:
            v = df[field].iloc[0]
            return v if pd.notnull(v) else None
        return None
    
    # Convert relevant columns to numeric for calculations
    def safe_float(val):
        """Convert a value to float, handling B/M/K suffixes and None/NaN."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                val = val.strip().replace(",", "").upper()
                if val == '' or val == 'NONE':
                    return None
                if val.endswith("B"):
                    return float(val[:-1]) * 1_000_000_000
                elif val.endswith("M"):
                    return float(val[:-1]) * 1_000_000
                elif val.endswith("K"):
                    return float(val[:-1]) * 1_000
                else:
                    return float(val)
            return float(val)
        except (ValueError, TypeError):
            return None

    # Extract and calculate all relevant values
    # Calculate TTM (trailing twelve months) EPS by summing last 4 quarters
    eps_ttm = None
    if "quarterlyBasicEPS" in inc.columns and len(inc["quarterlyBasicEPS"]) >= 4:
        eps_ttm = sum([safe_float(e) for e in inc["quarterlyBasicEPS"].iloc[:4] if safe_float(e) is not None])
    # Book Value Per Share: quarterlyTangibleBookValue (total) / shares outstanding
    tangible_book_total = safe_float(get_latest(bal, "quarterlyTangibleBookValue"))
    # Try to get shares outstanding from financials or balance sheet
    shares_out = None
    # Try common fields for shares outstanding
    for shares_field in ["quarterlySharesOutstanding", "quarterlyOrdinarySharesNumber", "quarterlyCommonStockSharesOutstanding"]:
        shares_out = safe_float(get_latest(bal, shares_field))
        if shares_out not in (None, 0):
            break
    bvps = tangible_book_total / shares_out if tangible_book_total not in (None, 0) and shares_out not in (None, 0) else None
    if "quarterlyTotalDebt" in bal.columns:
        total_debt = safe_float(get_latest(bal, "quarterlyTotalDebt"))
    else:
        total_debt = safe_float(get_latest(bal, ["quarterlyLongTermDebt", "quarterlyCurrentDebt"]))
    total_equity = safe_float(get_latest(bal, "quarterlyStockholdersEquity"))
    # For average equity, get value from 4 quarters ago
    equity_4q = None
    if "quarterlyStockholdersEquity" in bal.columns and len(bal["quarterlyStockholdersEquity"]) >= 5:
        equity_4q = safe_float(bal["quarterlyStockholdersEquity"].iloc[4])
    # Compute average equity if possible
    if total_equity is not None and equity_4q is not None:
        avg_equity = (total_equity + equity_4q) / 2
    else:
        avg_equity = total_equity
    # Calculate TTM (trailing twelve months) net income by summing last 4 quarters
    net_income_ttm = None
    if "quarterlyNetIncome" in inc.columns and len(inc["quarterlyNetIncome"]) >= 4:
        net_income_ttm = sum([safe_float(e) for e in inc["quarterlyNetIncome"].iloc[:4] if safe_float(e) is not None])
    total_revenue = safe_float(get_latest(inc, "quarterlyTotalRevenue"))
    # Net margin: use TTM (sum of last 4 quarters) net income and revenue
    net_income_ttm = None
    total_revenue_ttm = None
    if "quarterlyNetIncome" in inc.columns and len(inc["quarterlyNetIncome"]) >= 4:
        net_income_ttm = sum([safe_float(e) for e in inc["quarterlyNetIncome"].iloc[:4] if safe_float(e) is not None])
    if "quarterlyTotalRevenue" in inc.columns and len(inc["quarterlyTotalRevenue"]) >= 4:
        total_revenue_ttm = sum([safe_float(e) for e in inc["quarterlyTotalRevenue"].iloc[:4] if safe_float(e) is not None])

    # ROE: TTM Net Income / Average Equity (percent)
    roe = (net_income_ttm / avg_equity) * 100 if net_income_ttm is not None and avg_equity not in (None, 0) else None

    # Net Margin: TTM Net Income / TTM Total Revenue (percent)
    net_margin = (net_income_ttm / total_revenue_ttm) * 100 if net_income_ttm is not None and total_revenue_ttm not in (None, 0) and total_revenue_ttm > 0 else None

    # Revenue Growth (YoY): (Current Revenue - Revenue 4Q ago) / Revenue 4Q ago (percent)
    if "quarterlyTotalRevenue" in inc.columns and len(inc["quarterlyTotalRevenue"]) >= 5:
        rev_now = safe_float(get_latest(inc, "quarterlyTotalRevenue"))
        rev_4q = safe_float(get_latest(inc.iloc[4:], "quarterlyTotalRevenue"))
        revenue_growth_yoy = ((rev_now - rev_4q) / rev_4q) * 100 if rev_now is not None and rev_4q not in (None, 0) else None
    else:
        revenue_growth_yoy = None

    # Earnings Growth (YoY): (Current Net Income - Net Income 4Q ago) / Net Income 4Q ago (percent)
    if "quarterlyNetIncome" in inc.columns and len(inc["quarterlyNetIncome"]) >= 5:
        ni_now = safe_float(inc["quarterlyNetIncome"].iloc[0])
        ni_4q = safe_float(inc["quarterlyNetIncome"].iloc[4])
        earnings_growth_yoy = ((ni_now - ni_4q) / ni_4q) * 100 if ni_now is not None and ni_4q not in (None, 0) else None
    else:
        earnings_growth_yoy = None

    # Price (for PE/PB calculation)
    try:
        price_df = t.yahoo_api_price(range="1mo", dataGranularity="1d")
        price = safe_float(price_df["close"].iloc[-1])
    except Exception:
        price = None

    # PE Ratio: Price / TTM EPS
    pe_ratio = price / eps_ttm if price not in (None, 0) and eps_ttm not in (None, 0) and eps_ttm > 0 else None
    # PB Ratio: Price / Tangible Book Value Per Share
    pb_ratio = price / bvps if price not in (None, 0) and bvps not in (None, 0) else None
    # Standard PB Ratio: Price / (Total Stockholders' Equity per share)
    standard_bvps = total_equity / shares_out if total_equity not in (None, 0) and shares_out not in (None, 0) else None
    standard_pb_ratio = price / standard_bvps if price not in (None, 0) and standard_bvps not in (None, 0) else None
    # Debt/Equity: Total Debt / Total Equity
    debt_equity = total_debt / total_equity if total_debt not in (None, 0) and total_equity not in (None, 0) else None

    result = {
        "price": price,
        "eps_ttm": eps_ttm,
        "bvps": bvps,
        "standard_bvps": standard_bvps,
        "total_debt": total_debt,
        "total_equity": total_equity,
        "net_income_ttm": net_income_ttm,
        "total_revenue": total_revenue,
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "standard_pb_ratio": standard_pb_ratio,
        "debt_equity": debt_equity,
        "roe": roe,
        "net_margin": net_margin,
        "revenue_growth_yoy": revenue_growth_yoy,
        "earnings_growth_yoy": earnings_growth_yoy,
    }
    print(f"[stockdex-{symbol}] Final extracted fundamentals for {symbol}: {result}")
    return result
