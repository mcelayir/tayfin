"""HTTP client for the tayfin-ingestor API.

Used by indicator jobs to fetch index members and OHLCV data
without crossing schema boundaries (API-only rule).
"""

from __future__ import annotations

import os
import time
from datetime import date

import requests


class IngestorApiError(Exception):
    """Raised when the ingestor API returns a non-2xx response."""

    def __init__(self, status_code: int, body: str, url: str):
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"HTTP {status_code} from {url}: {body[:300]}")


_RETRYABLE_STATUS = {429, 503}


class IngestorClient:
    """Thin, resilient HTTP wrapper around tayfin-ingestor-api."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float | None = None,
        max_retries: int | None = None,
        backoff_s: float | None = None,
    ):
        self.base_url = (
            base_url
            or os.environ.get("TAYFIN_INGESTOR_API_BASE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.timeout_s = timeout_s or float(
            os.environ.get("TAYFIN_HTTP_TIMEOUT_SECONDS", "20")
        )
        self.max_retries = max_retries or int(
            os.environ.get("TAYFIN_HTTP_MAX_RETRIES", "3")
        )
        self.backoff_s = backoff_s or float(
            os.environ.get("TAYFIN_HTTP_BACKOFF_SECONDS", "1.0")
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_index_instruments(self, index_code: str) -> list[dict]:
        """Return instruments for *index_code* (at minimum ``ticker``)."""
        url = f"{self.base_url}/indices/members"
        params = {"index_code": index_code, "limit": "5000"}
        data = self._get_json(url, params)
        return data.get("items", [])

    def get_ohlcv_range(
        self,
        ticker: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return OHLCV candles for *ticker* as a list of dicts."""
        url = f"{self.base_url}/ohlcv"
        params: dict[str, str] = {"ticker": ticker}
        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()
        data = self._get_json(url, params)
        return data.get("items", [])

    # ------------------------------------------------------------------
    # Internal retry loop
    # ------------------------------------------------------------------

    def _get_json(self, url: str, params: dict) -> dict:
        """GET *url* with retry/backoff; return parsed JSON body."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout_s)
                if resp.ok:
                    return resp.json()
                # Retryable server errors
                if resp.status_code in _RETRYABLE_STATUS:
                    last_exc = IngestorApiError(resp.status_code, resp.text, url)
                    self._sleep(attempt)
                    continue
                # Non-retryable client/server error
                raise IngestorApiError(resp.status_code, resp.text, url)
            except requests.RequestException as exc:
                last_exc = exc
                self._sleep(attempt)
        # Exhausted retries
        raise last_exc  # type: ignore[misc]

    def _sleep(self, attempt: int) -> None:
        time.sleep(self.backoff_s * attempt)
