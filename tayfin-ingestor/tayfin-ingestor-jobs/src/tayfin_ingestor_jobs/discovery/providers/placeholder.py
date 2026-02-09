from typing import Iterable


class PlaceholderIndexDiscoveryProvider:
    """Placeholder provider for Phase 3 — returns empty list.

    Task 3 will implement a real provider that implements the same interface.
    """

    def discover(self, target_cfg: dict) -> Iterable[dict]:
        # Return empty set as placeholder
        return []
