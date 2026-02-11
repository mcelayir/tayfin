from .interfaces import IFundamentalsProvider


from .providers.stockdex_provider import create_provider as _create_stockdex_provider

def create_provider(country: str) -> IFundamentalsProvider:
    """Return a provider implementation based on country.

    For US instruments return the Stockdex Yahoo provider.
    """
    if country == "US":
        return _create_stockdex_provider()
    raise NotImplementedError(f"No fundamentals provider for country={country}")
