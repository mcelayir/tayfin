"""Factory for selecting the correct OHLCV provider based on job config."""
from __future__ import annotations

from .tradingview_provider import TradingViewOhlcvProvider
from .tradingview_screener_provider import TradingViewScreenerOhlcvProvider


def ohlcv_provider_factory(cfg: dict) -> TradingViewOhlcvProvider | TradingViewScreenerOhlcvProvider:
    """Return the appropriate primary OHLCV provider for the given job config.

    Parameters
    ----------
    cfg : dict
        OHLCV job config dict (as read from ``ohlcv.yml`` or ``ohlcv_backfill.yml``).
        Relevant keys: ``country``, ``index_code``.

    Returns
    -------
    IOhlcvProvider
        ``TradingViewScreenerOhlcvProvider`` for Turkey/BIST.
        ``TradingViewOhlcvProvider`` for everything else.
    """
    country = str(cfg.get("country", "")).upper()
    index_code = str(cfg.get("index_code", "")).upper()

    if country == "TR" and index_code == "BIST":
        return TradingViewScreenerOhlcvProvider(
            market="turkey",
            index_id="SYML:BIST;XU100",
        )

    return TradingViewOhlcvProvider()
