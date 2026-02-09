from typing import Protocol, Iterable


class IIndexDiscoveryProvider(Protocol):
    def discover(self, target_cfg: dict) -> Iterable[dict]:
        """Discover index members for the given target config.

        Returns an iterable of dicts with keys: ticker, country, index_code
        """
        ...
