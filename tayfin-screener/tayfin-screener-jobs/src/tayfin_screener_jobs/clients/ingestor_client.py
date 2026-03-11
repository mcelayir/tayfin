"""HTTP client for the tayfin-ingestor API.

Uses httpx per TECH_STACK_RULES §5.  Retries bounded to 3 attempts on
429 (rate-limited) and 503 (unavailable) with exponential back-off.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"
_MAX_INDEX_MEMBERS = 5000
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class IngestorClient:
    """Thin HTTP wrapper around tayfin-ingestor-api."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TAYFIN_INGESTOR_API_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.timeout = httpx.Timeout(timeout_s)
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------

    def get_index_members(
        self,
        index_code: str,
        country: str = "US",
    ) -> list[dict]:
        """Return constituent instruments for *index_code*.

        Each item is a dict with keys ``instrument_id``, ``symbol``,
        ``country``.  Returns an empty list when the index is unknown (404).
        """
        params: dict[str, str | int] = {
            "index_code": index_code,
            "country": country,
            "limit": _MAX_INDEX_MEMBERS,
        }
        data = self._get("/indices/members", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    def get_ohlcv_range(
        self,
        ticker: str,
        from_date: str,
        to_date: str,
    ) -> list[dict]:
        """Return OHLCV candles for *ticker* between *from_date* and *to_date*.

        Dates are ``YYYY-MM-DD`` strings.  Returns an empty list when the
        ticker is not found (404).
        """
        params: dict[str, str] = {
            "ticker": ticker,
            "from": from_date,
            "to": to_date,
        }
        data = self._get("/ohlcv", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    def get_fundamentals_latest(
        self,
        symbol: str,
        country: str = "US",
        source: str | None = None,
    ) -> dict | None:
        """Return the latest fundamentals snapshot for *symbol*.

        The API and DB lookup are ticker + date based; callers SHOULD NOT rely
        on a specific provider *source*. When *source* is provided it will be
        passed to the API; when omitted the client will request by ticker/country
        only (no source query param).

        Returns a flat dict with keys such as ``revenue_growth_yoy``,
        ``earnings_growth_yoy``, ``roe``, ``net_margin``, ``debt_equity``,
        etc.  Returns ``None`` when the symbol has no fundamentals (404).
        """
        params: dict[str, str] = {
            "symbol": symbol,
            "country": country,
        }
        if source is not None:
            params["source"] = source
        return self._get("/fundamentals/latest", params=params, allow_404=True)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        params: dict | None = None,
        allow_404: bool = False,
    ) -> dict | None:
        """Issue a GET with bounded retry on 429 / 503.

        Returns the parsed JSON body on success.  Returns ``None`` when the
        server replies 404 **and** *allow_404* is True.  Raises
        ``httpx.HTTPStatusError`` for any other non-2xx status.
        """
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            resp = httpx.get(url, params=params, timeout=self.timeout)
            if resp.status_code in (429, 503) and attempt <= self.max_retries:
                delay = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "Ingestor %s returned %s – retry %d/%d in %.1fs",
                    path,
                    resp.status_code,
                    attempt,
                    self.max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            break

        if allow_404 and resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
