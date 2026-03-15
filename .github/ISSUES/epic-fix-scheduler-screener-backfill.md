# Epic: Fix scheduler & screener/backfill failures

**Type:** Bug Epic
**Status:** Draft

## Summary
After merging to `main`, scheduled screener jobs appear not to run and `ohlcv_backfill_weekly` is failing. This epic diagnoses and fixes packaging/config, scheduler invocation, and job resilience so scheduled flows run reliably end-to-end.

## Key references
- Project description: docs/architecture/tayfin_project_documentation.md
- Architecture rules: docs/architecture/ARCHITECTURE_RULES.md
- ADRs: docs/architecture/adr/
- Tech stack: docs/architecture/TECH_STACK_RULES.md
- Planning protocol: docs/ai/COPILOT_TASK_PLANNING_GUIDE.md

## Acceptance criteria
- Scheduler executes `mcsa_screen`, `vcp_screen`, and `ohlcv_backfill_weekly` successfully in staging.
- `ohlcv_backfill_weekly` reports clear outcomes (success/skip/failure) and does not crash due to missing discovery.
- Config files are available in runtime images or invoked explicitly; CLI no longer errors with missing job/target.
- Tests added and CI includes a scheduler smoke check.
- ADRs updated if contract/packaging changes occur.

## Phases & Tasks

### Phase 0 — (done) Triage
| ID | Task | Owner |
|---:|---|---|
| 1 | Investigate scheduler & job-runner failures; gather logs & reproduce locally | Screener / Infra |
| 2 | Reproduce failing jobs locally (PYTHONPATH / editable install) | Screener |
| 3 | Root-cause analysis (config, packaging, services) | PM / lead-dev |

### Phase 1 — Packaging & Config (High priority)
| ID | Task | Owner |
|---:|---|---|
| 6 | Ensure config files are present at runtime (package files into image or mount and use explicit `--config`) | Infra / Packaging |
| 9 | Update `infra/schedules.yml` to use explicit `--config` paths and sensible env/timeouts | Infra |

### Phase 2 — Job resilience & correctness
| ID | Task | Owner |
|---:|---|---|
| 7 | Improve `ohlcv_backfill` to handle empty instruments gracefully and provide actionable error messages | Ingestor |
| 8 | Harden provider calls with retries/backoff and ensure idempotent upserts | Ingestor / Screener |

### Phase 3 — Tests & CI
| ID | Task | Owner |
|---:|---|---|
| 10 | Add unit/integration tests for CLI missing-config and backfill empty-instruments paths | QA / Screener / Ingestor |
| CI | Add infra smoke job to CI to run `scheduler --once` against mocked endpoints | Infra / CI |

### Phase 4 — Staging deploy & validation
| ID | Task | Owner |
|---:|---|---|
| 12 | Deploy updated images/config to staging and validate scheduled flows | Ops / lead-dev |
| 11 | Update docs and record ADRs for any contract or packaging changes | lead-dev / docs |

### Phase 5 — Monitor, rollout & close
| ID | Task | Owner |
|---:|---|---|
| 13 | Monitor production runs for 48–72h, phased rollout | Ops / lead-dev |
| 14 | Postmortem and epic closeout | PM / lead-dev |

## Immediate next steps
1. Attach scheduler job stdout/stderr from failing runs into this issue (scheduler prints these already). @lead-dev please review.
2. Choose infra-first (explicit `--config` + image mount) or code-first (add `load_config` fallback). Infra-first is lower risk and faster.

## Notes & Risks
- If discovery has not been run, backfill will logically fail until instruments exist — this is an operational dependency.
- Packaging changes must ensure `config/*.yml` are discoverable at runtime.

---

/cc @lead-dev
