import httpx
import pandas as pd
import logging
from typing import Iterable


class NasdaqTraderIndexDiscoveryProvider:
    """Provider that fetches NASDAQ-100 constituents from Nasdaq API.

    The provider returns a pandas.DataFrame internally but exposes a
    discover(...) method that returns an iterable of dicts (records),
    and also keeps the DataFrame available via `last_dataframe` for
    consumers that need it.
    """

    URL = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.last_dataframe: pd.DataFrame | None = None

    def _fetch_json(self) -> list[dict]:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(self.URL, headers=self.HEADERS)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch NASDAQ-100 list: HTTP {resp.status_code}")
        payload = resp.json()
        rows = payload.get("data", {}).get("data", {}).get("rows")
        if not rows:
            raise RuntimeError("No rows found in NASDAQ API response")
        return rows

    def discover(self, target_cfg: dict) -> Iterable[dict]:
        """Discover returns an iterable of dicts (to satisfy the job interface).

        It also stores a DataFrame in `last_dataframe` matching the spec.
        """
        rows = self._fetch_json()

        country = target_cfg.get("country", "US")
        index_code = target_cfg.get("index_code", "NDX")

        tickers = []
        for row in rows:
            symbol = row.get("symbol", "").strip().upper()
            if symbol:
                tickers.append(symbol)

        df = pd.DataFrame({"ticker": tickers})
        df = df.drop_duplicates(subset=["ticker"])
        df["country"] = country
        df["index_code"] = index_code
        df = df[["ticker", "country", "index_code"]].copy()

        self.last_dataframe = df
        logging.info(f"Discovered {len(df)} tickers from Nasdaq API for {index_code}")

        return df
