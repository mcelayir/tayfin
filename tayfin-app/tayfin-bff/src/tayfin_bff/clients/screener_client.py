"""HTTP client for the tayfin-screener API.

Uses httpx per TECH_STACK_RULES §5.  Retries bounded to 3 attempts on
429 / 503 with exponential back-off.

The BFF calls the Screener API to retrieve precomputed MCSA and VCP
results.  It MUST NOT query the screener database directly
(ARCHITECTURE_RULES §2.1).
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:8020"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


class ScreenerClient:
    """Thin httpx wrapper around the tayfin-screener-api endpoints."""

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

    def get_mcsa_latest_all(self, *, params: dict | None = None) -> dict | None:
        """GET /mcsa/latest — all tickers, latest per ticker."""
        return self._get("/mcsa/latest", params=params)

    def get_mcsa_latest_ticker(self, ticker: str) -> dict | None:
        """GET /mcsa/latest/<ticker> — single ticker result."""
        return self._get(f"/mcsa/latest/{ticker}", allow_404=True)

    def get_mcsa_range(
        self, *, ticker: str, from_date: str, to_date: str
    ) -> dict | None:
        """GET /mcsa/range — date range for a ticker."""
        return self._get(
            "/mcsa/range",
            params={"ticker": ticker, "from": from_date, "to": to_date},
        )

    # ------------------------------------------------------------------
    # VCP endpoints (for future use)
    # ------------------------------------------------------------------

    def get_vcp_latest_all(self, *, params: dict | None = None) -> dict | None:
        """GET /vcp/latest — all tickers, latest VCP result per ticker."""
        return self._get("/vcp/latest", params=params)

    def get_vcp_latest_ticker(self, ticker: str) -> dict | None:
        """GET /vcp/latest/<ticker> — single ticker VCP result."""
        return self._get(f"/vcp/latest/{ticker}", allow_404=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        params: dict | None = None,
        allow_404: bool = False,
    ) -> dict | None:
        """GET with bounded retry on 429/503.

        Returns parsed JSON on success, ``None`` on 404 (if allowed) or
        on connection failure.
        """
        url = f"{self.base_url}{path}"
        attempt = 0

        while True:
            attempt += 1
            try:
                resp = httpx.get(url, params=params, timeout=self.timeout)
            except httpx.ConnectError:
                logger.warning(
                    "ScreenerClient: connection refused for %s (attempt %d/%d)",
                    url,
                    attempt,
                    self.max_retries,
                )
                if attempt <= self.max_retries:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue
                return None
            except httpx.TimeoutException:
                logger.warning(
                    "ScreenerClient: timeout for %s (attempt %d/%d)",
                    url,
                    attempt,
                    self.max_retries,
                )
                if attempt <= self.max_retries:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue
                return None

            if resp.status_code in (429, 503) and attempt <= self.max_retries:
                delay = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "ScreenerClient: %s returned %d, retrying in %.1fs",
                    url,
                    resp.status_code,
                    delay,
                )
                time.sleep(delay)
                continue

            break

        if allow_404 and resp.status_code == 404:
            return None

        if resp.status_code >= 400:
            logger.error(
                "ScreenerClient: %s returned %d: %s",
                url,
                resp.status_code,
                resp.text[:200],
            )
            return None

        return resp.json()
