"""Stockdex-based fundamentals provider.

Fetches financial data via Stockdex's Yahoo API methods and computes
standard fundamental metrics. Falls back to yfinance if Stockdex fails.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from ..interfaces import IFundamentalsProvider
from ._helpers import safe_float, div
from ._yfinance_fallback import yfinance_fallback

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def _pick_field(df: Optional[pd.DataFrame], candidates: List[str]) -> Optional[str]:
    """Return the first column name from *candidates* that exists in *df*."""
    if df is None:
        return None
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _latest(df: Optional[pd.DataFrame], field: Any) -> Optional[float]:
    """Extract the latest (first-row) value for *field* from *df*."""
    if df is None or df.empty:
        return None
    if isinstance(field, list):
        for f in field:
            if f in df.columns:
                v = safe_float(df[f].iloc[0])
                if v is not None:
                    return v
        return None
    if field in df.columns:
        return safe_float(df[field].iloc[0])
    return None


def _ttm(df: Optional[pd.DataFrame], field: str) -> Optional[float]:
    """Sum the last 4 quarters (trailing-twelve-months) for *field*."""
    if df is None or field not in df.columns:
        return None
    vals = [safe_float(x) for x in df[field].iloc[:4]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def _prior_ttm(df: Optional[pd.DataFrame], field: str) -> Optional[float]:
    """Sum quarters 5-8 (prior-year TTM) for *field*."""
    if df is None or field not in df.columns:
        return None
    if len(df[field]) < 8:
        return None
    vals = [safe_float(x) for x in df[field].iloc[4:8]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


# ---------------------------------------------------------------------------
# Metric resolvers — each returns (value, trace_dict)
# ---------------------------------------------------------------------------

def _resolve_eps(inc: Optional[pd.DataFrame]) -> tuple[Optional[float], dict]:
    trace: dict = {"tried": []}
    candidates = [
        ("quarterlyBasicEPS", True),
        ("quarterlyDilutedEPS", True),
        ("annualDilutedEPS", False),
        ("annualBasicEPS", False),
    ]
    for col, is_quarterly in candidates:
        if is_quarterly:
            val = _ttm(inc, col)
            trace["tried"].append({"column": col, "method": "ttm", "value": val})
        else:
            val = _latest(inc, col)
            trace["tried"].append({"column": col, "method": "latest", "value": val})
        if val not in (None, 0):
            trace["chosen"] = col
            return val, trace
    return None, trace


def _resolve_shares(bal: Optional[pd.DataFrame]) -> tuple[Optional[float], dict]:
    trace: dict = {"tried": []}
    candidates = [
        "quarterlyOrdinarySharesNumber",
        "quarterlySharesOutstanding",
        "quarterlyCommonStockSharesOutstanding",
        "annualOrdinarySharesNumber",
        "annualBasicAverageShares",
    ]
    for col in candidates:
        val = _latest(bal, col)
        trace["tried"].append({"column": col, "value": val})
        if val not in (None, 0):
            trace["chosen"] = col
            return val, trace
    return None, trace


def _resolve_bvps(bal: Optional[pd.DataFrame], shares: Optional[float]) -> tuple[Optional[float], dict]:
    trace: dict = {"tried": []}
    candidates = ["quarterlyTangibleBookValue", "annualTangibleBookValue", "quarterlyNetTangibleAssets"]
    for col in candidates:
        val = _latest(bal, col)
        trace["tried"].append({"column": col, "value": val})
        if val not in (None, 0) and shares not in (None, 0):
            trace["chosen"] = col
            return div(val, shares), trace
    return None, trace


def _resolve_single(df: Optional[pd.DataFrame], candidates: List[str]) -> tuple[Optional[float], dict]:
    """Pick the first non-null latest value from *candidates*."""
    trace: dict = {"tried": []}
    for col in candidates:
        val = _latest(df, col)
        trace["tried"].append({"column": col, "value": val})
        if val is not None:
            trace["chosen"] = col
            return val, trace
    return None, trace


def _resolve_ttm_metric(inc: Optional[pd.DataFrame], q_col: str, a_col: str) -> tuple[Optional[float], dict]:
    """Resolve a TTM metric: try quarterly TTM first, then annual latest."""
    trace: dict = {"tried": []}
    val = _ttm(inc, q_col)
    trace["tried"].append({"column": q_col, "method": "ttm", "value": val})
    if val not in (None, 0):
        trace["chosen"] = q_col
        return val, trace
    val = _latest(inc, a_col)
    trace["tried"].append({"column": a_col, "method": "latest", "value": val})
    if val not in (None, 0):
        trace["chosen"] = a_col
        return val, trace
    return None, trace


def _resolve_revenue(inc: Optional[pd.DataFrame]) -> tuple[Optional[float], dict]:
    trace: dict = {"tried": []}
    val = _ttm(inc, "quarterlyTotalRevenue")
    trace["tried"].append({"column": "quarterlyTotalRevenue", "method": "ttm", "value": val})
    if val not in (None, 0):
        trace["chosen"] = "quarterlyTotalRevenue (ttm)"
        return val, trace
    val = _latest(inc, "quarterlyTotalRevenue")
    trace["tried"].append({"column": "quarterlyTotalRevenue", "method": "latest", "value": val})
    if val not in (None, 0):
        trace["chosen"] = "quarterlyTotalRevenue (latest)"
        return val, trace
    val = _latest(inc, "annualTotalRevenue")
    trace["tried"].append({"column": "annualTotalRevenue", "method": "latest", "value": val})
    if val not in (None, 0):
        trace["chosen"] = "annualTotalRevenue"
        return val, trace
    return None, trace


def _resolve_growth(
    inc_q: Optional[pd.DataFrame],
    inc_a: Optional[pd.DataFrame],
    q_col: str,
    a_col: str,
) -> tuple[Optional[float], dict]:
    """Compute YoY growth.

    Strategy 1: quarterly TTM (rows 0-3) vs prior-year TTM (rows 4-7).
    Strategy 2: annual income statement — latest vs previous year.
    """
    trace: dict = {}

    # Strategy 1 — quarterly TTM vs prior TTM
    current = _ttm(inc_q, q_col)
    prior = _prior_ttm(inc_q, q_col)
    trace["quarterly_ttm"] = current
    trace["prior_quarterly_ttm"] = prior
    if current not in (None, 0) and prior not in (None, 0):
        trace["chosen"] = "quarterly_ttm_vs_prior"
        return div(current - prior, prior) * 100, trace

    # Strategy 2 — annual DataFrame (separate fetch)
    if inc_a is not None and a_col in inc_a.columns:
        vals = inc_a[a_col].tolist()
        # vals are ordered oldest→newest (index is date-ascending)
        # pick the last two non-null values
        valid = [(i, safe_float(v)) for i, v in enumerate(vals) if safe_float(v) not in (None, 0)]
        trace["annual_values"] = [(i, v) for i, v in valid]
        if len(valid) >= 2:
            a_prev_val = valid[-2][1]
            a_now_val = valid[-1][1]
            trace["annual_now"] = a_now_val
            trace["annual_prev"] = a_prev_val
            trace["chosen"] = "annual_latest_vs_prev"
            return div(a_now_val - a_prev_val, a_prev_val) * 100, trace

    return None, trace


def _resolve_price(ticker_obj) -> tuple[Optional[float], dict]:
    trace: dict = {}
    try:
        price_df = ticker_obj.yahoo_api_price(range="1mo", dataGranularity="1d")
        if price_df is not None and not price_df.empty and "close" in price_df.columns:
            price = safe_float(price_df["close"].iloc[-1])
            trace["chosen"] = "yahoo_api_price.close"
            trace["value"] = price
            return price, trace
    except Exception:
        pass
    return None, trace


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class StockdexProvider:
    """Fundamentals provider using Stockdex Yahoo API with yfinance fallback."""

    SOURCE_ID = "stockdex_yahoo"

    def _fetch_datasets(self, ticker_obj) -> tuple[
        Optional[pd.DataFrame],
        Optional[pd.DataFrame],
        Optional[pd.DataFrame],
        Optional[pd.DataFrame],
    ]:
        """Fetch quarterly financials/income/balance + annual income statement."""
        fin, inc, bal, inc_annual = None, None, None, None
        for attr, freq in [
            ("yahoo_api_financials", "quarterly"),
            ("yahoo_api_income_statement", "quarterly"),
            ("yahoo_api_balance_sheet", "quarterly"),
        ]:
            try:
                df = getattr(ticker_obj, attr)(frequency=freq)
            except Exception:
                try:
                    df = getattr(ticker_obj, attr)()
                except Exception:
                    df = None
            if attr == "yahoo_api_financials":
                fin = df
            elif attr == "yahoo_api_income_statement":
                inc = df
            else:
                bal = df

        # Annual income statement — needed for YoY growth fallback
        try:
            inc_annual = ticker_obj.yahoo_api_income_statement(frequency="annual")
        except Exception:
            inc_annual = None

        return fin, inc, bal, inc_annual

    def _compute_avg_equity(self, bal: Optional[pd.DataFrame], equity_now: Optional[float]) -> Optional[float]:
        """Average equity over 4 quarters for ROE calculation."""
        equity_4q = None
        if bal is not None and "quarterlyStockholdersEquity" in bal.columns and len(bal["quarterlyStockholdersEquity"]) >= 5:
            equity_4q = safe_float(bal["quarterlyStockholdersEquity"].iloc[4])
        if equity_now not in (None, 0) and equity_4q not in (None, 0):
            return (equity_now + equity_4q) / 2
        return equity_now

    def _compute_via_stockdex(self, ticker: str) -> Dict[str, Any]:
        """Primary path: compute fundamentals using Stockdex."""
        from stockdex import Ticker

        sym = ticker.split(":", 1)[1] if ":" in ticker else ticker
        t = Ticker(ticker=sym)

        _fin, inc, bal, inc_annual = self._fetch_datasets(t)
        trace: Dict[str, Any] = {}

        # Resolve individual metrics
        eps_ttm, trace["eps_ttm"] = _resolve_eps(inc)
        shares_out, trace["shares_out"] = _resolve_shares(bal)
        bvps, trace["bvps"] = _resolve_bvps(bal, shares_out)
        total_debt, trace["total_debt"] = _resolve_single(bal, ["quarterlyTotalDebt", "annualTotalDebt", "quarterlyLongTermDebt", "annualLongTermDebt"])
        total_equity, trace["total_equity"] = _resolve_single(bal, ["quarterlyStockholdersEquity", "annualStockholdersEquity", "annualTotalEquityGrossMinorityInterest"])
        net_income_ttm, trace["net_income_ttm"] = _resolve_ttm_metric(inc, "quarterlyNetIncome", "annualNetIncome")
        total_revenue, trace["total_revenue"] = _resolve_revenue(inc)
        price, trace["price"] = _resolve_price(t)
        revenue_growth_yoy, trace["revenue_growth_yoy"] = _resolve_growth(inc, inc_annual, "quarterlyTotalRevenue", "annualTotalRevenue")
        earnings_growth_yoy, trace["earnings_growth_yoy"] = _resolve_growth(inc, inc_annual, "quarterlyNetIncome", "annualNetIncome")

        # Derived ratios
        avg_equity = self._compute_avg_equity(bal, total_equity)
        roe = div(net_income_ttm, avg_equity) * 100 if net_income_ttm not in (None, 0) and avg_equity not in (None, 0) else None

        revenue_ttm = _ttm(inc, "quarterlyTotalRevenue")
        if revenue_ttm not in (None, 0) and net_income_ttm not in (None, 0):
            net_margin = div(net_income_ttm, revenue_ttm) * 100
        elif total_revenue not in (None, 0) and net_income_ttm not in (None, 0):
            net_margin = div(net_income_ttm, total_revenue) * 100
        else:
            net_margin = None

        pe_ratio = div(price, eps_ttm) if price not in (None, 0) and eps_ttm not in (None, 0) else None
        pb_ratio = div(price, bvps) if price not in (None, 0) and bvps not in (None, 0) else None

        standard_bvps = div(total_equity, shares_out) if total_equity not in (None, 0) and shares_out not in (None, 0) else None
        standard_pb_ratio = div(price, standard_bvps) if price not in (None, 0) and standard_bvps not in (None, 0) else None
        debt_equity = div(total_debt, total_equity) if total_debt not in (None, 0) and total_equity not in (None, 0) else None

        return {
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
            "source": self.SOURCE_ID,
            "as_of_date": date.today(),
            "trace": trace,
        }

    def compute(self, ticker: str, country: str) -> Dict[str, Any]:
        try:
            return self._compute_via_stockdex(ticker)
        except Exception as exc:
            logger.warning("Stockdex failed for %s, falling back to yfinance: %s", ticker, exc)
            sym = ticker.split(":", 1)[1] if ":" in ticker else ticker
            result = yfinance_fallback(sym)
            result["source"] = self.SOURCE_ID
            result["as_of_date"] = date.today()
            return result


def create_provider() -> StockdexProvider:
    return StockdexProvider()
