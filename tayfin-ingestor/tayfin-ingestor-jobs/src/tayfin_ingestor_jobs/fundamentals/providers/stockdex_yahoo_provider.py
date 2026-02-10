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

            # Fetch preferred structured datasets (quarterly where available)
            fin = None
            inc = None
            bal = None
            try:
                fin = t.yahoo_api_financials(frequency="quarterly")
            except Exception:
                try:
                    fin = t.yahoo_api_financials()
                except Exception:
                    fin = None
            try:
                inc = t.yahoo_api_income_statement(frequency="quarterly")
            except Exception:
                try:
                    inc = t.yahoo_api_income_statement()
                except Exception:
                    inc = None
            try:
                bal = t.yahoo_api_balance_sheet(frequency="quarterly")
            except Exception:
                try:
                    bal = t.yahoo_api_balance_sheet()
                except Exception:
                    bal = None

            # traceability map for debugging/inspection
            trace: Dict[str, Any] = {}

            def pick_field(df: Optional[pd.DataFrame], candidates: List[str]) -> Optional[str]:
                if df is None:
                    return None
                for c in candidates:
                    if c in df.columns:
                        return c
                return None

            def ttm_from_quarters(df: Optional[pd.DataFrame], field: str) -> Optional[float]:
                if df is None or field not in df.columns:
                    return None
                vals = [_safe_float(x) for x in df[field].iloc[:4]]
                vals = [v for v in vals if v is not None]
                if not vals:
                    return None
                return sum(vals)

            def prior_year_ttm_from_quarters(df: Optional[pd.DataFrame], field: str) -> Optional[float]:
                if df is None or field not in df.columns:
                    return None
                if len(df[field]) >= 8:
                    vals = [_safe_float(x) for x in df[field].iloc[4:8]]
                    vals = [v for v in vals if v is not None]
                    if not vals:
                        return None
                    return sum(vals)
                return None

            def latest_from(df: Optional[pd.DataFrame], field: Any) -> Optional[float]:
                if df is None or df.empty:
                    return None
                if isinstance(field, list):
                    for f in field:
                        if f in df.columns:
                            v = _safe_float(df[f].iloc[0])
                            if v is not None:
                                return v
                    return None
                if field in df.columns:
                    return _safe_float(df[field].iloc[0])
                return None

            # Metric mapping preferences - prefer structured yahoo_api quarterly fields,
            # fall back to annuals and other datasets where necessary.
            # We'll compute each metric and record trace information.

            # EPS TTM
            eps_ttm = None
            eps_trace: Dict[str, Any] = {"tried": []}
            eps_candidates = ["quarterlyBasicEPS", "quarterlyDilutedEPS", "annualDilutedEPS", "annualBasicEPS"]
            for cand in eps_candidates:
                if cand.startswith("quarterly"):
                    val = ttm_from_quarters(inc, cand)
                    eps_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": cand, "value": val})
                    if val not in (None, 0):
                        eps_ttm = val
                        eps_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": cand, "method": "ttm_from_quarters"}
                        break
                else:
                    v = latest_from(inc, cand)
                    eps_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": cand, "value": v})
                    if v not in (None, 0):
                        eps_ttm = v
                        eps_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": cand, "method": "annual_latest"}
                        break
            trace["eps_ttm"] = eps_trace

            # Shares outstanding heuristics (for BVPS)
            shares_out = None
            shares_trace: Dict[str, Any] = {"tried": []}
            shares_candidates = [
                "quarterlyOrdinarySharesNumber",
                "quarterlySharesOutstanding",
                "quarterlyCommonStockSharesOutstanding",
                "annualOrdinarySharesNumber",
                "annualBasicAverageShares",
            ]
            for sf in shares_candidates:
                v = latest_from(bal, sf)
                shares_trace["tried"].append({"dataset": "yahoo_api_balance_sheet", "column": sf, "value": v})
                if v not in (None, 0):
                    shares_out = v
                    shares_trace["chosen"] = {"dataset": "yahoo_api_balance_sheet", "column": sf}
                    break
            trace["shares_out"] = shares_trace

            # BVPS: prefer tangible book value (quarterly) / shares
            bvps = None
            bvps_trace: Dict[str, Any] = {"tried": []}
            tb_candidates = ["quarterlyTangibleBookValue", "annualTangibleBookValue", "quarterlyNetTangibleAssets"]
            for tb in tb_candidates:
                tval = latest_from(bal, tb)
                bvps_trace["tried"].append({"dataset": "yahoo_api_balance_sheet", "column": tb, "value": tval})
                if tval not in (None, 0) and shares_out not in (None, 0):
                    bvps = _div(tval, shares_out)
                    bvps_trace["chosen"] = {"dataset": "yahoo_api_balance_sheet", "column": tb}
                    break
            trace["bvps"] = bvps_trace

            # total debt & total equity
            debt_trace: Dict[str, Any] = {"tried": []}
            td = pick_field(bal, ["quarterlyTotalDebt", "annualTotalDebt", "quarterlyLongTermDebt", "annualLongTermDebt"])
            if td:
                debt_val = latest_from(bal, td)
                debt_trace["chosen"] = {"dataset": "yahoo_api_balance_sheet", "column": td, "value": debt_val}
                total_debt = debt_val
            else:
                total_debt = None
            trace["total_debt"] = debt_trace

            eq_trace: Dict[str, Any] = {"tried": []}
            te = pick_field(bal, ["quarterlyStockholdersEquity", "annualStockholdersEquity", "annualTotalEquityGrossMinorityInterest"])
            if te:
                te_val = latest_from(bal, te)
                eq_trace["chosen"] = {"dataset": "yahoo_api_balance_sheet", "column": te, "value": te_val}
                total_equity = te_val
            else:
                total_equity = None
            trace["total_equity"] = eq_trace

            # average equity (try quarterly lookback)
            equity_now = total_equity
            equity_4q = None
            if bal is not None and "quarterlyStockholdersEquity" in bal.columns and len(bal["quarterlyStockholdersEquity"]) >= 5:
                equity_4q = _safe_float(bal["quarterlyStockholdersEquity"].iloc[4])
            if equity_now not in (None, 0) and equity_4q not in (None, 0):
                avg_equity = (equity_now + equity_4q) / 2
            else:
                avg_equity = equity_now

            # Net income TTM and revenue TTM: prefer quarterly aggregation
            net_income_ttm = None
            nit_trace: Dict[str, Any] = {"tried": []}
            for cand in ["quarterlyNetIncome", "annualNetIncome"]:
                if cand.startswith("quarterly"):
                    v = ttm_from_quarters(inc, cand)
                    nit_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": cand, "value": v})
                    if v not in (None, 0):
                        net_income_ttm = v
                        nit_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": cand, "method": "ttm_from_quarters"}
                        break
                else:
                    v = latest_from(inc, cand)
                    nit_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": cand, "value": v})
                    if v not in (None, 0):
                        net_income_ttm = v
                        nit_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": cand, "method": "annual_latest"}
                        break
            trace["net_income_ttm"] = nit_trace

            total_revenue = None
            tr_trace: Dict[str, Any] = {"tried": []}
            # try quarterly TTM then latest quarterly then annual
            tr_tt = ttm_from_quarters(inc, "quarterlyTotalRevenue")
            tr_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": "quarterlyTotalRevenue", "ttm": tr_tt})
            if tr_tt not in (None, 0):
                total_revenue = tr_tt
                tr_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": "quarterlyTotalRevenue", "method": "ttm_from_quarters"}
            else:
                q_latest = latest_from(inc, "quarterlyTotalRevenue")
                tr_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": "quarterlyTotalRevenue_latest", "value": q_latest})
                if q_latest not in (None, 0):
                    total_revenue = q_latest
                    tr_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": "quarterlyTotalRevenue", "method": "latest_quarter"}
                else:
                    a_latest = latest_from(inc, "annualTotalRevenue")
                    tr_trace["tried"].append({"dataset": "yahoo_api_income_statement", "column": "annualTotalRevenue", "value": a_latest})
                    if a_latest not in (None, 0):
                        total_revenue = a_latest
                        tr_trace["chosen"] = {"dataset": "yahoo_api_income_statement", "column": "annualTotalRevenue", "method": "annual_latest"}
            trace["total_revenue"] = tr_trace

            roe = None
            if net_income_ttm not in (None, 0) and avg_equity not in (None, 0):
                roe = _div(net_income_ttm, avg_equity) * 100

            net_margin = None
            # net margin: prefer net_income_ttm / revenue_ttm when possible
            revenue_ttm = None
            revenue_ttm = ttm_from_quarters(inc, "quarterlyTotalRevenue")
            if revenue_ttm not in (None, 0) and net_income_ttm not in (None, 0):
                net_margin = _div(net_income_ttm, revenue_ttm) * 100
            elif total_revenue not in (None, 0) and net_income_ttm not in (None, 0):
                net_margin = _div(net_income_ttm, total_revenue) * 100

            # revenue YoY (try comparing TTM to prior-year TTM)
            revenue_growth_yoy = None
            rev_trace: Dict[str, Any] = {"tried": []}
            rev_ttm = ttm_from_quarters(inc, "quarterlyTotalRevenue")
            prior_rev_ttm = prior_year_ttm_from_quarters(inc, "quarterlyTotalRevenue")
            rev_trace["quarterly_ttm"] = rev_ttm
            rev_trace["prior_quarterly_ttm"] = prior_rev_ttm
            if rev_ttm not in (None, 0) and prior_rev_ttm not in (None, 0):
                revenue_growth_yoy = _div((rev_ttm - prior_rev_ttm), prior_rev_ttm) * 100
                rev_trace["chosen"] = {"method": "quarterly_ttm_vs_prior_ttm"}
            else:
                # fallback to annual comparison
                a_now = latest_from(inc, "annualTotalRevenue")
                # try previous annual (second row)
                a_prev = None
                try:
                    if inc is not None and "annualTotalRevenue" in inc.columns and len(inc["annualTotalRevenue"]) >= 2:
                        a_prev = _safe_float(inc["annualTotalRevenue"].iloc[1])
                except Exception:
                    a_prev = None
                rev_trace["annual_now"] = a_now
                rev_trace["annual_prev"] = a_prev
                if a_now not in (None, 0) and a_prev not in (None, 0):
                    revenue_growth_yoy = _div((a_now - a_prev), a_prev) * 100
                    rev_trace["chosen"] = {"method": "annual_latest_vs_prev"}
            trace["revenue_growth_yoy"] = rev_trace

            # earnings YoY (same approach)
            earnings_growth_yoy = None
            earn_trace: Dict[str, Any] = {"tried": []}
            net_ttm = net_income_ttm
            prior_net_ttm = prior_year_ttm_from_quarters(inc, "quarterlyNetIncome")
            earn_trace["quarterly_ttm"] = net_ttm
            earn_trace["prior_quarterly_ttm"] = prior_net_ttm
            if net_ttm not in (None, 0) and prior_net_ttm not in (None, 0):
                earnings_growth_yoy = _div((net_ttm - prior_net_ttm), prior_net_ttm) * 100
                earn_trace["chosen"] = {"method": "quarterly_ttm_vs_prior_ttm"}
            else:
                a_now = latest_from(inc, "annualNetIncome")
                a_prev = None
                try:
                    if inc is not None and "annualNetIncome" in inc.columns and len(inc["annualNetIncome"]) >= 2:
                        a_prev = _safe_float(inc["annualNetIncome"].iloc[1])
                except Exception:
                    a_prev = None
                earn_trace["annual_now"] = a_now
                earn_trace["annual_prev"] = a_prev
                if a_now not in (None, 0) and a_prev not in (None, 0):
                    earnings_growth_yoy = _div((a_now - a_prev), a_prev) * 100
                    earn_trace["chosen"] = {"method": "annual_latest_vs_prev"}
            trace["earnings_growth_yoy"] = earn_trace

            # price (prefer structured yahoo_api_price close)
            price = None
            price_trace: Dict[str, Any] = {"tried": []}
            try:
                price_df = t.yahoo_api_price(range="1mo", dataGranularity="1d")
                if price_df is not None and not price_df.empty and "close" in price_df.columns:
                    # take last available close
                    price = _safe_float(price_df["close"].iloc[-1])
                    price_trace["chosen"] = {"dataset": "yahoo_api_price", "column": "close", "value": price}
            except Exception:
                price = None
            trace["price"] = price_trace

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
            out["trace"] = trace
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
