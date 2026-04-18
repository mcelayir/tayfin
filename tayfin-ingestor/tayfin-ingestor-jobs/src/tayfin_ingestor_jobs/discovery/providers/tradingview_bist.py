import logging
from typing import Iterable

import pandas as pd
from tradingview_screener import Query, Column


class TradingViewBistDiscoveryProvider:
    """Provider that fetches all Borsa Istanbul (BIST) instruments from TradingView.

    Uses tradingview_screener.Query with set_markets('turkey'), which returns
    symbols prefixed with 'BIST:'. The prefix is stripped before returning,
    and results are deduplicated and sorted alphabetically.
    """

    def __init__(self):
        pass

    def discover(self, target_cfg: dict) -> Iterable[dict]:
        """Discover BIST instruments.

        Returns an iterable of dicts with keys: ticker, country, index_code.
        """

        raw_count, raw_df = (
            Query()
            .set_markets('turkey')
            .set_index('SYML:BIST;XU100')
            .select('name', 'exchange', 'market', 'is_primary', 'indexes')
            .where(Column('is_primary') == True)  # Filter for primary listings to reduce duplicates
            .limit(5000)
            .get_scanner_data()
        )
        
        if raw_df is None or raw_df.empty:
            raise RuntimeError("No symbols returned from TradingView for market='turkey'")

        logging.info(f"[provider] TradingView returned {raw_count} raw symbols for market=turkey")

        # raw_df['ticker'] contains 'BIST:SYMBOL' format — strip the exchange prefix
        tickers_raw = raw_df['ticker'].tolist()
        tickers = [t.replace('BIST:', '', 1).strip().upper() for t in tickers_raw if t.startswith('BIST:')]

        # Deduplicate preserving insertion order, then sort alphabetically
        unique_tickers = sorted(dict.fromkeys(tickers))

        country = target_cfg.get("country", "TR")
        index_code = target_cfg.get("index_code", "BIST")
        exchange = target_cfg.get("exchange", "BIST")

        result = [
            {"ticker": t, "country": country, "index_code": index_code, "exchange": exchange}
            for t in unique_tickers
        ]

        logging.info(f"Discovered {len(result)} tickers from TradingView for {index_code}")

        return result
