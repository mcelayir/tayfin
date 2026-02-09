import httpx
import pandas as pd
import io
import re
import html as _html
import unicodedata
from typing import Iterable


class NasdaqTraderIndexDiscoveryProvider:
    """Provider that fetches NASDAQ-100 constituents from NasdaqTrader HTML.

    The provider returns a pandas.DataFrame internally but exposes a
    discover(...) method that returns an iterable of dicts (records),
    and also keeps the DataFrame available via `last_dataframe` for
    consumers that need it.
    """

    URL = "https://www.nasdaqtrader.com/dynamic/nasdaq100ndx.stm"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.last_dataframe: pd.DataFrame | None = None

    def _fetch_html(self) -> str:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.URL)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch NASDAQ list: {resp.status_code}")
        return resp.text

    def _parse_tables(self, html: str) -> pd.DataFrame:
        # Let pandas parse all tables and find the one with a symbol/ticker column
        tables = pd.read_html(io.StringIO(html))
        for df in tables:
            cols = [c.lower() for c in df.columns.astype(str)]
            for candidate in ("symbol", "ticker", "sym"):
                for i, c in enumerate(cols):
                    if candidate in c:
                        colname = df.columns[i]
                        # Normalize, unescape HTML entities and strip whitespace
                        def clean_token(x: str) -> str:
                            if x is None:
                                return ""
                            s = str(x)
                            # Unescape HTML entities (convert '&nbsp;' -> non-breaking space)
                            s = _html.unescape(s)
                            # Normalize unicode (NFKC) and replace non-breaking and other spaces
                            s = unicodedata.normalize("NFKC", s)
                            # Replace any whitespace (including NBSP) with empty string
                            s = re.sub(r"\s+", "", s)
                            s = s.strip().upper()
                            return s

                        ser = df[colname].astype(str).map(clean_token)
                        ser = ser[ser.notnull()]
                        ser = ser[ser != ""]
                        ser = ser.drop_duplicates()
                        # Keep only reasonable ticker tokens (letters, numbers, dot, hyphen)
                        ser = ser[ser.str.match(r"^[A-Z0-9.\-]+$")]
                        # Filter obvious invalid tokens (common HTML artifacts or placeholders)
                        blacklist = {"NAN", "N/A", "NA", "", "NONE"}
                        ser = ser[~ser.isin(blacklist)]
                        out = pd.DataFrame({"ticker": ser.values})
                        return out
        raise RuntimeError("Could not find ticker column in NasdaqTrader tables")

    def discover(self, target_cfg: dict) -> Iterable[dict]:
        """Discover returns an iterable of dicts (to satisfy the job interface).

        It also stores a DataFrame in `last_dataframe` matching the spec.
        """
        html = self._fetch_html()
        df = self._parse_tables(html)

        country = target_cfg.get("country", "US")
        index_code = target_cfg.get("index_code", "NDX")

        df["country"] = country
        df["index_code"] = index_code

        # Keep canonical ordering and types
        df = df[["ticker", "country", "index_code"]].copy()

        self.last_dataframe = df

        # Return the DataFrame (caller may iterate over records if needed)
        return df
