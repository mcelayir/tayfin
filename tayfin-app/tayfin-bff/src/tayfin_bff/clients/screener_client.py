"""HTTP client for the tayfin-screener API.

Uses httpx per TECH_STACK_RULES §5.  Retries bounded to 3 attempts on
429 (rate-limited) and 503 (unavailable) with exponential back-off.

The BFF uses this client to proxy screener data to the HTMX UI
(§2.2 — UI calls only BFF; BFF calls context APIs).
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8020"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class ScreenerClient:
    """Thin HTTP wrapper around tayfin-screener-api."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("TAYFIN_SCREENER_API_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.timeout = httpx.Timeout(timeout_s)
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # MCSA endpoints
    # ------------------------------------------------------------------

    def get_mcsa_latest(
        self,
        *,
        pass_only: bool = False,
        min_criteria: int | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        """Return latest MCSA results for all tickers.

        Returns a list of MCSA result dicts.  Returns [] on 404.
        """
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if pass_only:
            params["pass_only"] = "true"
        if min_criteria is not None:
            params["min_criteria"] = min_criteria

        data = self._get("/mcsa/latest", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    def get_mcsa_latest_ticker(self, ticker: str) -> dict | None:
        """Return the latest MCSA result for one ticker.

        Returns ``None`` when no data exists (404).
        """
        return self._get(
            f"/mcsa/latest/{ticker.upper()}", allow_404=True,
        )

    def get_mcsa_range(
        self,
        ticker: str,
        from_date: str,
        to_date: str,
    ) -> list[dict]:
        """Return MCSA results for *ticker* over a date range.

        Returns an empty list on 404.
        """
        params: dict[str, str] = {
            "ticker": ticker.upper(),
            "from": from_date,
            "to": to_date,
        }
        data = self._get("/mcsa/range", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    # ------------------------------------------------------------------
    # VCP endpoints (for future dashboard use)
    # ------------------------------------------------------------------

    def get_vcp_latest(
        self,
        *,
        pattern_only: bool = False,
        min_score: float | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        """Return latest VCP results for all tickers."""
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if pattern_only:
            params["pattern_only"] = "true"
        if min_score is not None:
            params["min_score"] = min_score

        data = self._get("/vcp/latest", params=params, allow_404=True)
        if data is None:
            return []
        return data.get("items", [])

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> bool:
        """Return True if the screener API is reachable."""
        try:
            data = self._get("/health")
            return data is not None and data.get("status") == "ok"
        except Exception:
            return False

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
                    "Screener %s returned %s – retry %d/%d in %.1fs",
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
