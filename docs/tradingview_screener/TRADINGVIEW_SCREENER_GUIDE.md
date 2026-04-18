# tradingview-screener — Capability Guide

This document captures findings from the spike run against `tradingview-screener==2.5.0` for the `turkey` market, executed as part of Issue #41.

## Package identity

| Attribute | Value |
|-----------|-------|
| PyPI package name | `tradingview-screener` |
| Python import name | `tradingview_screener` |
| Pinned version | `2.5.0` |
| **Distinct from** | `tradingview-scraper` (different PyPI package already in requirements) |

## Spike results (Issue #41, 2026-04-18)

| Assertion | Result |
|-----------|--------|
| Import `from tradingview_screener import get_all_symbols` | ✅ Pass |
| `get_all_symbols(market='turkey')` returns `list` | ✅ Pass |
| Symbol count for `market='turkey'` | **630 symbols** |
| All symbols prefixed with `BIST:` | ✅ 630/630 |
| No authentication required | ✅ Confirmed — works without env vars or session cookies |

## Usage pattern

```python
from tradingview_screener import get_all_symbols

raw: list[str] = get_all_symbols(market="turkey")
# Returns e.g. ['BIST:MAKIM', 'BIST:BRMEN', 'BIST:TNZTP', ...]
```

## Transformation for Tayfin storage

Strip the `BIST:` prefix before storing — the unique constraint on `instruments` is `(ticker, country)`:

```python
ticker = symbol.replace("BIST:", "", 1).strip().upper()
```

## Rate limits / reliability

- No rate limiting observed during spike.
- No TradingView account or cookie required for `get_all_symbols`.
- Call latency at spike time: < 1 second.

## Spike test location

`tayfin-ingestor/tayfin-ingestor-jobs/tests/spikes/test_tradingview_screener_spike.py`
