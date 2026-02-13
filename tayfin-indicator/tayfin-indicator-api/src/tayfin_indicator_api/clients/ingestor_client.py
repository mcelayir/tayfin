"""HTTP client for the tayfin-ingestor API.

Used by the indicator API to fetch index membership data.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

# Maximum number of index members to fetch
MAX_INDEX_MEMBERS = 5000


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
        params = {"index_code": index_code, "limit": str(MAX_INDEX_MEMBERS)}
        try:
            resp = requests.get(url, params=params, timeout=self.timeout_s)
            if resp.ok:
                data = resp.json()
                # Extract ticker symbols from the response
                return [item["symbol"] for item in data.get("items", [])]
            logger.warning(
                "Failed to fetch index members for %s: HTTP %s",
                index_code,
                resp.status_code,
            )
            return []
        except Exception as exc:
            # If the ingestor API is unavailable, return empty list
            # This allows the endpoint to gracefully degrade
            logger.warning(
                "Exception fetching index members for %s: %s",
                index_code,
                exc,
            )
            return []
