from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
import time
import random

from ..interfaces import IFundamentalsProvider


class StockdexProviderError(Exception):
    pass


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            if pd.isna(val):
                return None
            return float(val)
        if isinstance(val, str):
            v = val.strip().replace(",", "").upper()
            if v in ("", "N/A", "NONE"):
                return None
            if v.endswith("B"):
                return float(v[:-1]) * 1_000_000_000
            if v.endswith("M"):
                return float(v[:-1]) * 1_000_000
            if v.endswith("K"):
                return float(v[:-1]) * 1_000
            return float(v)
        return float(val)
    except Exception:
        return None


def _latest_value(df: pd.DataFrame, field: Any) -> Optional[float]:
    if df is None or df.empty:
        return None
    if isinstance(field, list):
        vals: List[float] = []
        for f in field:
            if f in df.columns:
                v = _safe_float(df[f].iloc[0])
                if v is not None:
                    vals.append(v)
        return sum(vals) if vals else None
    if field in df.columns:
        return _safe_float(df[field].iloc[0])
    return None


def _sum_ttm(df: pd.DataFrame, field: str) -> Optional[float]:
    if df is None or field not in df.columns:
        return None
    vals = [_safe_float(x) for x in df[field].iloc[:4] if _safe_float(x) is not None]
    if not vals:
        return None
    return sum(vals)


def _div(n: Optional[float], d: Optional[float]) -> Optional[float]:
    if n is None or d in (None, 0):
        return None
    try:
        return float(n) / float(d)
    except Exception:
        return None


class StockdexYahooProvider:
    SOURCE_ID = "stockdex_yahoo"

    def compute(self, ticker: str, country: str) -> Dict[str, Any]:
        sym = ticker.split(":", 1)[1] if ":" in ticker else ticker

        # First, try using stockdex (preferred)
        stockdex_exc: Optional[Exception] = None
        try:
            from stockdex import Ticker

            t = Ticker(ticker=sym)

            fin = t.yahoo_api_financials(frequency="quarterly")
            inc = t.yahoo_api_income_statement(frequency="quarterly")
            bal = t.yahoo_api_balance_sheet(frequency="quarterly")

            # EPS TTM: sum last 4 quarters
            eps_ttm = _sum_ttm(inc, "quarterlyBasicEPS")

            # Shares outstanding heuristics
            shares_out = None
            for shares_field in [
                "quarterlySharesOutstanding",
                "quarterlyOrdinarySharesNumber",
                "quarterlyCommonStockSharesOutstanding",
            ]:
                shares_out = _latest_value(bal, shares_field)
                if shares_out not in (None, 0):
                    break

            tangible_book_total = _latest_value(bal, "quarterlyTangibleBookValue")
            bvps = None
            if tangible_book_total not in (None, 0) and shares_out not in (None, 0):
                bvps = _div(tangible_book_total, shares_out)

            # total debt
            if "quarterlyTotalDebt" in bal.columns:
                total_debt = _latest_value(bal, "quarterlyTotalDebt")
            else:
                total_debt = _latest_value(bal, ["quarterlyLongTermDebt", "quarterlyCurrentDebt"])

            total_equity = _latest_value(bal, "quarterlyStockholdersEquity")

            # average equity
            equity_now = total_equity
            equity_4q = None
            if "quarterlyStockholdersEquity" in bal.columns and len(bal["quarterlyStockholdersEquity"]) >= 5:
                equity_4q = _safe_float(bal["quarterlyStockholdersEquity"].iloc[4])
            if equity_now not in (None, 0) and equity_4q not in (None, 0):
                avg_equity = (equity_now + equity_4q) / 2
            else:
                avg_equity = equity_now

            net_income_ttm = _sum_ttm(inc, "quarterlyNetIncome")
            total_revenue = _latest_value(inc, "quarterlyTotalRevenue")
            total_revenue_ttm = _sum_ttm(inc, "quarterlyTotalRevenue")

            roe = None
            if net_income_ttm not in (None, 0) and avg_equity not in (None, 0):
                roe = _div(net_income_ttm, avg_equity) * 100

            net_margin = None
            if net_income_ttm not in (None, 0) and total_revenue_ttm not in (None, 0):
                net_margin = _div(net_income_ttm, total_revenue_ttm) * 100

            revenue_growth_yoy = None
            if "quarterlyTotalRevenue" in inc.columns and len(inc["quarterlyTotalRevenue"]) >= 5:
                rev_now = _latest_value(inc, "quarterlyTotalRevenue")
                rev_4q = _safe_float(inc["quarterlyTotalRevenue"].iloc[4])
                if rev_now not in (None, 0) and rev_4q not in (None, 0):
                    revenue_growth_yoy = _div((rev_now - rev_4q), rev_4q) * 100

            earnings_growth_yoy = None
            if "quarterlyNetIncome" in inc.columns and len(inc["quarterlyNetIncome"]) >= 5:
                ni_now = _safe_float(inc["quarterlyNetIncome"].iloc[0])
                ni_4q = _safe_float(inc["quarterlyNetIncome"].iloc[4])
                if ni_now not in (None, 0) and ni_4q not in (None, 0):
                    earnings_growth_yoy = _div((ni_now - ni_4q), ni_4q) * 100

            # price
            try:
                price_df = t.yahoo_api_price(range="1mo", dataGranularity="1d")
                price = _safe_float(price_df["close"].iloc[-1])
            except Exception:
                price = None

            # ratios
            pe_ratio = None
            if price not in (None, 0) and eps_ttm not in (None, 0):
                pe_ratio = _div(price, eps_ttm)

            pb_ratio = None
            if price not in (None, 0) and bvps not in (None, 0):
                pb_ratio = _div(price, bvps)

            standard_bvps = None
            if total_equity not in (None, 0) and shares_out not in (None, 0):
                standard_bvps = _div(total_equity, shares_out)

            standard_pb_ratio = None
            if price not in (None, 0) and standard_bvps not in (None, 0):
                standard_pb_ratio = _div(price, standard_bvps)

            debt_equity = None
            if total_debt not in (None, 0) and total_equity not in (None, 0):
                debt_equity = _div(total_debt, total_equity)

            result: Dict[str, Optional[float]] = {
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

            out: Dict[str, Any] = {**result}
            out["source"] = self.SOURCE_ID
            out["as_of_date"] = date.today()
            return out
        except Exception as stockdex_exc:
            # stockdex failed or raised runtime error — attempt yfinance fallback with retries
            try:
                import yfinance as yf
            except Exception as e:
                raise StockdexProviderError(f"stockdex_yahoo provider failed for {ticker}: stockdex error: {stockdex_exc}; fallback import failed: {e}") from e

            max_attempts = 4
            base_delay = 1.0
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    t = yf.Ticker(sym)
                    info = t.info or {}

                    eps_ttm = _safe_float(info.get("trailingEps"))
                    price = _safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
                    bvps = _safe_float(info.get("bookValue"))
                    shares_out = _safe_float(info.get("sharesOutstanding"))
                    total_debt = _safe_float(info.get("totalDebt") or info.get("longTermDebt"))
                    total_equity = _safe_float(info.get("totalStockholderEquity")) or (_safe_float(info.get("bookValue")) * shares_out if bvps not in (None, 0) and shares_out not in (None, 0) else None)

                    net_income_ttm = None
                    total_revenue = None
                    total_revenue_ttm = None
                    roe = None
                    net_margin = _safe_float(info.get("profitMargins")) * 100 if _safe_float(info.get("profitMargins")) is not None else None
                    revenue_growth_yoy = None
                    earnings_growth_yoy = None

                    pe_ratio = _safe_float(info.get("trailingPE"))
                    pb_ratio = _safe_float(info.get("priceToBook")) or (_div(price, bvps) if price not in (None, 0) and bvps not in (None, 0) else None)
                    standard_bvps = bvps
                    standard_pb_ratio = None if standard_bvps in (None, 0) or price in (None, 0) else _div(price, standard_bvps)
                    debt_equity = None if total_debt in (None, 0) or total_equity in (None, 0) else _div(total_debt, total_equity)

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

                    out = {**result}
                    out["source"] = self.SOURCE_ID
                    out["as_of_date"] = date.today()
                    return out
                except Exception as e:
                    last_exc = e
                    if attempt < max_attempts:
                        jitter = random.uniform(0, 0.5)
                        delay = base_delay * (2 ** (attempt - 1)) + jitter
                        print(f"[stockdex fallback] attempt {attempt} failed for {ticker}: {e}; retrying in {delay:.2f}s", flush=True)
                        time.sleep(delay)
                        continue
                    raise StockdexProviderError(f"stockdex_yahoo provider failed for {ticker}: stockdex error: {stockdex_exc}; fallback error after {max_attempts} attempts: {last_exc}") from last_exc


# Expose as IFundamentalsProvider-compatible factory
def create_provider() -> IFundamentalsProvider:
    return StockdexYahooProvider()
