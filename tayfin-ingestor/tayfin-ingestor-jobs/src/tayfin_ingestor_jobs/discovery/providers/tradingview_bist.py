import logging
from typing import Iterable

from tradingview_screener import get_all_symbols


class TradingViewBistDiscoveryProvider:
    """Provider that fetches all Borsa Istanbul (BIST) instruments from TradingView.

    Uses tradingview_screener.get_all_symbols(market='turkey') which returns
    symbols prefixed with 'BIST:'. The prefix is stripped before returning,
    and results are deduplicated and sorted alphabetically.
    """

    def __init__(self):
        pass

    def discover(self, target_cfg: dict) -> Iterable[dict]:
        """Discover BIST instruments.

        Returns an iterable of dicts with keys: ticker, country, index_code.
        """
        raw: list[str] = get_all_symbols(market="turkey")

        if not raw:
            raise RuntimeError("No symbols returned from TradingView for market='turkey'")

        tickers = []
        for symbol in raw:
            stripped = symbol.replace("BIST:", "", 1).strip().upper()
            if stripped:
                tickers.append(stripped)

        # Deduplicate preserving insertion order, then sort alphabetically
        unique_tickers = sorted(dict.fromkeys(tickers))

        country = target_cfg.get("country", "TR")
        index_code = target_cfg.get("index_code", "BIST")

        result = [
            {"ticker": t, "country": country, "index_code": index_code}
            for t in unique_tickers
        ]

        logging.info(f"Discovered {len(result)} tickers from TradingView for {index_code}")

        return result
