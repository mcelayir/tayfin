"""Unit tests for TradingViewBistDiscoveryProvider.

No DB connection. No real network calls. No DiscoveryJob instantiation.
All calls to get_all_symbols are mocked via unittest.mock.patch.

Patch target: "tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"
"""
import pytest
from unittest.mock import patch

PATCH_TARGET = "tayfin_ingestor_jobs.discovery.providers.tradingview_bist.get_all_symbols"
CFG = {"country": "TR", "index_code": "BIST"}


def make_provider():
    from tayfin_ingestor_jobs.discovery.providers.tradingview_bist import TradingViewBistDiscoveryProvider
    return TradingViewBistDiscoveryProvider()


def test_strip_prefix():
    with patch(PATCH_TARGET, return_value=["BIST:AKBNK"]):
        result = list(make_provider().discover(CFG))
    assert len(result) == 1
    assert result[0]["ticker"] == "AKBNK"


def test_sorted_alphabetically():
    with patch(PATCH_TARGET, return_value=["BIST:ZZZCO", "BIST:AKBNK", "BIST:THYAO"]):
        result = list(make_provider().discover(CFG))
    assert [r["ticker"] for r in result] == ["AKBNK", "THYAO", "ZZZCO"]


def test_deduplication():
    with patch(PATCH_TARGET, return_value=["BIST:AKBNK", "BIST:AKBNK", "BIST:THYAO"]):
        result = list(make_provider().discover(CFG))
    assert len(result) == 2


def test_dict_keys():
    with patch(PATCH_TARGET, return_value=["BIST:AKBNK"]):
        result = list(make_provider().discover(CFG))
    assert len(result) == 1
    assert set(result[0].keys()) == {"ticker", "country", "index_code"}


def test_country_from_config():
    with patch(PATCH_TARGET, return_value=["BIST:AKBNK"]):
        result = list(make_provider().discover({"country": "TR", "index_code": "BIST"}))
    assert result[0]["country"] == "TR"


def test_index_code_from_config():
    with patch(PATCH_TARGET, return_value=["BIST:AKBNK"]):
        result = list(make_provider().discover({"country": "TR", "index_code": "BIST"}))
    assert result[0]["index_code"] == "BIST"


def test_raises_on_empty():
    with patch(PATCH_TARGET, return_value=[]):
        with pytest.raises(RuntimeError):
            list(make_provider().discover(CFG))


def test_combined():
    """Full integration of dedup + sort + prefix strip on a mixed input."""
    with patch(PATCH_TARGET, return_value=["BIST:ZZZCO", "BIST:AKBNK", "BIST:AKBNK", "BIST:THYAO"]):
        result = list(make_provider().discover(CFG))

    tickers = [r["ticker"] for r in result]

    # 3 unique results
    assert len(result) == 3, f"Expected 3 unique results, got {len(result)}"

    # sorted alphabetically
    assert tickers == sorted(tickers), f"Not sorted: {tickers}"

    # no BIST: prefix
    assert all(not t.startswith("BIST:") for t in tickers), f"Prefix found in: {tickers}"

    # correct keys on all dicts
    for row in result:
        assert set(row.keys()) == {"ticker", "country", "index_code"}
