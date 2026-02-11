"""yfinance fallback for when Stockdex fails.

Provides a thin wrapper that fetches fundamentals from yfinance with
exponential-backoff retry logic.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Optional

from ._helpers import safe_float, div

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
BASE_DELAY = 1.0


class YFinanceFallbackError(Exception):
    pass


def yfinance_fallback(symbol: str) -> Dict[str, Any]:
    """Fetch fundamentals from yfinance with retry logic.

    Returns a dict matching the same metric keys as the primary Stockdex
    provider so the caller can merge seamlessly.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise YFinanceFallbackError(f"yfinance is not installed") from exc

    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}

            eps_ttm = safe_float(info.get("trailingEps"))
            price = safe_float(info.get("regularMarketPrice") or info.get("previousClose"))
            bvps = safe_float(info.get("bookValue"))
            shares_out = safe_float(info.get("sharesOutstanding"))
            total_debt = safe_float(info.get("totalDebt") or info.get("longTermDebt"))

            total_equity = safe_float(info.get("totalStockholderEquity"))
            if total_equity is None and bvps not in (None, 0) and shares_out not in (None, 0):
                total_equity = bvps * shares_out

            profit_margins = safe_float(info.get("profitMargins"))
            net_margin = profit_margins * 100 if profit_margins is not None else None

            pe_ratio = safe_float(info.get("trailingPE"))
            pb_ratio = safe_float(info.get("priceToBook")) or (
                div(price, bvps) if price not in (None, 0) and bvps not in (None, 0) else None
            )

            standard_bvps = bvps
            standard_pb_ratio = div(price, standard_bvps) if price not in (None, 0) and standard_bvps not in (None, 0) else None
            debt_equity = div(total_debt, total_equity) if total_debt not in (None, 0) and total_equity not in (None, 0) else None

            return {
                "price": price,
                "eps_ttm": eps_ttm,
                "bvps": bvps,
                "standard_bvps": standard_bvps,
                "total_debt": total_debt,
                "total_equity": total_equity,
                "net_income_ttm": None,
                "total_revenue": None,
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "standard_pb_ratio": standard_pb_ratio,
                "debt_equity": debt_equity,
                "roe": None,
                "net_margin": net_margin,
                "revenue_growth_yoy": None,
                "earnings_growth_yoy": None,
            }
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                jitter = random.uniform(0, 0.5)
                delay = BASE_DELAY * (2 ** (attempt - 1)) + jitter
                logger.warning(
                    "yfinance attempt %d/%d failed for %s: %s; retrying in %.2fs",
                    attempt, MAX_ATTEMPTS, symbol, exc, delay,
                )
                time.sleep(delay)
            else:
                raise YFinanceFallbackError(
                    f"yfinance fallback failed for {symbol} after {MAX_ATTEMPTS} attempts: {last_exc}"
                ) from last_exc
