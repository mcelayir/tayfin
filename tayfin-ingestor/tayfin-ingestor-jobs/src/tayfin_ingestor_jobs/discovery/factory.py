from ..discovery.providers.placeholder import PlaceholderIndexDiscoveryProvider
from ..discovery.providers.nasdaqtrader import NasdaqTraderIndexDiscoveryProvider


def create_provider(target_cfg: dict):
    """Create an index discovery provider for the given target config.

    Returns a NasdaqTrader provider when the config `code` is nasdaq100 or
    when the target key uses the dash form (nasdaq-100). Falls back to the
    placeholder provider otherwise.
    """
    if not target_cfg:
        return PlaceholderIndexDiscoveryProvider()

    code = str(target_cfg.get("code", "") or "").lower()
    # Accept both 'nasdaq100' and 'nasdaq-100' (factory key may be dashed)
    if code in ("nasdaq100", "nasdaq-100"):
        return NasdaqTraderIndexDiscoveryProvider()

    return PlaceholderIndexDiscoveryProvider()
