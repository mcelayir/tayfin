"""HTTP client for the tayfin-indicator API.

Uses httpx per TECH_STACK_RULES §5.  Retries bounded to 3 attempts on
429 (rate-limited) and 503 (unavailable) with exponential back-off.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8010"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class IndicatorClient:
    """Thin HTTP wrapper around tayfin-indicator-api."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TAYFIN_INDICATOR_API_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.timeout = httpx.Timeout(timeout_s)
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------

    def get_latest(
        self,
        ticker: str,
        indicator: str,
        window: int | None = None,
    ) -> dict | None:
        """Return the most recent indicator value for *ticker*.

        Returns a dict with keys ``ticker``, ``as_of_date``, ``indicator``,
        ``params``, ``value``, ``source``.  Returns ``None`` when no data
        is found (404).
        """
        params: dict[str, str | int] = {
            "ticker": ticker,
            "indicator": indicator,
        }
        if window is not None:
            params["window"] = window
        return self._get("/indicators/latest", params=params, allow_404=True)

    def get_range(
        self,
        ticker: str,
        indicator: str,
        from_date: str,
        to_date: str,
        window: int | None = None,
    ) -> list[dict]:
        """Return a time-series of indicator values for *ticker*.

        Each item is a dict with keys ``as_of_date`` and ``value``.
        Returns an empty list when no data is found (404).
        """
        params: dict[str, str | int] = {
            "ticker": ticker,
            "indicator": indicator,
            "from": from_date,
            "to": to_date,
        }
        if window is not None:
            params["window"] = window
        data = self._get("/indicators/range", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    def get_index_latest(
        self,
        index_code: str,
        indicator: str,
        window: int | None = None,
    ) -> list[dict]:
        """Return the latest indicator value per ticker for all index members.

        Each item is a dict with keys ``ticker``, ``as_of_date``, ``value``.
        Returns an empty list when no data is found.
        """
        params: dict[str, str | int] = {
            "index_code": index_code,
            "indicator": indicator,
        }
        if window is not None:
            params["window"] = window
        data = self._get(
            "/indicators/index/latest", params=params, allow_404=True,
        )
        if data is None:
            return []
        return data.get("items", [])

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
                    "Indicator %s returned %s – retry %d/%d in %.1fs",
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
