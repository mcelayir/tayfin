"""HTTP client for the tayfin-ingestor API.

Used by the indicator API to fetch index membership data.
"""

from __future__ import annotations

import os

import requests


class IngestorClient:
    """Thin HTTP wrapper around tayfin-ingestor-api."""

    def __init__(self, base_url: str | None = None, timeout_s: float = 10.0):
        self.base_url = (
            base_url
            or os.environ.get("TAYFIN_INGESTOR_API_BASE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.timeout_s = timeout_s

    def get_index_members(self, index_code: str) -> list[str]:
        """Return list of tickers for the given index_code."""
        url = f"{self.base_url}/indices/members"
        params = {"index_code": index_code, "limit": "5000"}
        try:
            resp = requests.get(url, params=params, timeout=self.timeout_s)
            if resp.ok:
                data = resp.json()
                # Extract ticker symbols from the response
                return [item["symbol"] for item in data.get("items", [])]
            return []
        except Exception:
            # If the ingestor API is unavailable, return empty list
            # This allows the endpoint to gracefully degrade
            return []
