# Tech Debt #1 — Upgrade `tradingview-screener` from 2.5.0 to latest

## Description

`tradingview-screener` is currently pinned at `2.5.0` in
`tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`. The latest
release is **v3.1.0** (February 2026), which includes a rewritten `Query()`
API and breaking changes from the 2.x series.

## Affected Files

- `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt`
- `tayfin-ingestor/tayfin-ingestor-jobs/src/tayfin_ingestor_jobs/discovery/providers/tradingview_bist.py`

## Why Out of Scope for Issue #42

Issue #42 is scoped to creating an agent skill (documentation + scripts).
It does not modify any production code or `requirements.txt`. Upgrading the
pinned version requires validating that `TradingViewBistDiscoveryProvider`
continues to work correctly with the v3.x API, which is a separate
engineering task.

## Suggested Next Steps

1. Install `tradingview-screener>=3.1.0` in a dev environment.
2. Run the existing unit tests for `TradingViewBistDiscoveryProvider`.
3. Run the spike script at `tayfin-ingestor/tayfin-ingestor-jobs/tests/spikes/test_tradingview_screener_spike.py`.
4. If all tests pass, update `requirements.txt` and open a PR.
5. Update the field catalogue in `.github/skills/tradingview-screener/references/fields.md`
   if any new fields are available in v3.x.

## Logged by

Developer Agent — Issue #42 pre-work
