## Epic: Investigate MCSA scoring components and weighting

Date: 2026-03-11

Summary
-------
Initial investigation into `MCSA` scoring indicates the VCP component is often dominating final scores in local runs. This doc captures quick findings and proposed next steps.

Quick findings
--------------
- Configured weights (from `tayfin-screener-jobs/config/screener.yml`):
  - trend: 30
  - vcp: 35
  - volume: 15
  - fundamentals: 20
- In local test runs (NDX full run) many indicator/latest endpoints returned 404 for some windows, and fundamentals queries often returned 404. When components lack data the scoring implementation currently may still attribute full weight to VCP, resulting in VCP-dominated MCSA scores.
- Logs show many `indicators/latest` calls returned 404 while `indicators/range` succeeded (range is used for time-series features). Missing latest values can reduce trend/volume contributions.

Initial hypotheses
------------------
1. Missing data handling: when a component's input is missing the scoring code may not be reducing that component's weight proportionally.
2. Normalization bug: component contributions might not be normalized properly before aggregation, allowing VCP to dominate.
3. Configuration vs runtime mismatch: the YAML weights may not be applied as expected in production code paths.

Planned investigation steps
-------------------------
1. Audit scoring code paths: review `tayfin-screener-jobs/src/tayfin_screener_jobs/mcsa/scoring.py` and related modules to confirm how missing inputs are handled and how weights are applied.
2. Add unit tests for edge cases: missing indicators, missing fundamentals, partial data.
3. Run component-contribution analysis on recent NDX run: calculate per-ticker component contributions (trend, vcp, vol, fund) and distribution statistics.
4. Propose remediation: either re-normalize weights when components missing, or revise the default missing-data mode (config `missing_data.mode`) and document trade-offs.

Deliverables
------------
- Code audit notes (this doc + inline PR comments)
- Unit tests covering missing-data and normalization
- Diagnostic job that outputs per-ticker component contributions
- Proposed fix PR (if straightforward) or ADR if architectural change required

QA checklist (for `qa` agent)
--------------------------------
- [ ] Re-run a full NDX pipeline on a clean DB snapshot and capture logs.
- [ ] Collect `tayfin_screener.mcsa_results` and verify per-row `evidence` / breakdown contains non-zero components beyond `vcp` for at least 30% of tickers.
- [ ] Confirm behavior when indicators/latest endpoints are 404: MCSA should gracefully degrade (either reweight or mark component as missing) and not give full weight to VCP.
- [ ] Validate new unit tests (after fix PR) pass locally and in CI.
- [ ] Compare score distribution (before vs after fix) and confirm changes align with expected weighting.

References
----------
- Config: `tayfin-screener/tayfin-screener-jobs/config/screener.yml`
- Scoring code: `tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/mcsa/scoring.py`

Notes
-----
This is an initial investigation. Next step: code audit and small diagnostic job to quantify component contributions.
