from typing import Protocol


class IFundamentalsProvider(Protocol):
    def compute(self, ticker: str, country: str) -> dict:
        """Compute fundamentals for a single ticker.

        Returns a dict whose keys match the columns in `fundamentals_snapshots`.
       """
        ...
