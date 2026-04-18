"""Spike: tradingview-screener==2.5.0 — validate get_all_symbols for turkey market.

Run manually (requires live network access to TradingView):
    cd tayfin-ingestor/tayfin-ingestor-jobs
    pytest tests/spikes/test_tradingview_screener_spike.py -v -s

This spike does NOT write to any database.
Findings documented in: docs/knowledge/tradingview_screener/
"""
import pytest


@pytest.mark.spike
def test_import_succeeds():
    """Library can be imported at the expected path."""
    from tradingview_screener import get_all_symbols  # noqa: F401


@pytest.mark.spike
def test_get_all_symbols_returns_list():
    """get_all_symbols(market='turkey') returns a non-empty list."""
    from tradingview_screener import get_all_symbols

    result = get_all_symbols(market="turkey")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 10, f"Expected >10 symbols, got {len(result)}. Possible API issue."


@pytest.mark.spike
def test_symbols_have_bist_prefix():
    """All (or most) returned symbols are prefixed with 'BIST:'."""
    from tradingview_screener import get_all_symbols

    result = get_all_symbols(market="turkey")
    bist_prefixed = [s for s in result if s.startswith("BIST:")]
    assert len(bist_prefixed) > 0, "No symbols with 'BIST:' prefix found — check market parameter."
    # Print for documentation purposes
    print(f"\n[spike] Total symbols returned: {len(result)}")
    print(f"[spike] BIST-prefixed symbols: {len(bist_prefixed)}")
    print(f"[spike] First 5: {result[:5]}")


@pytest.mark.spike
def test_no_auth_required():
    """Call succeeds without any session cookie or API key in environment."""
    import os
    from tradingview_screener import get_all_symbols

    # Explicitly verify no TradingView auth env vars are set
    tv_env_keys = [k for k in os.environ if "TRADINGVIEW" in k.upper()]
    assert not tv_env_keys, (
        f"TradingView env vars found: {tv_env_keys}. "
        "Remove them to confirm the call works without auth."
    )

    result = get_all_symbols(market="turkey")
    assert isinstance(result, list) and len(result) > 0
    print(f"\n[spike] Confirmed: no auth required. Got {len(result)} symbols.")
