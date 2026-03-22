# E36-03 — Draft PR

Title: feat(docs): Add canonical READMEs for tayfin-ingestor (E36-03)

Branch: `docs/issue-36/st-01-placeholders`

Description:
- Adds top-level and submodule README.md files for `tayfin-ingestor` (API + jobs) following the canonical template.
- Adds JSON Schema artifacts for `/fundamentals` and `/ohlcv` endpoints and a small local validator used by QA.
- Populates env var tables and provides runnable helper script `tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh`.

Files of note:
- `tayfin-ingestor/README.md`
- `tayfin-ingestor/tayfin-ingestor-api/README.md`
- `tayfin-ingestor/tayfin-ingestor-jobs/README.md`
- `tayfin-ingestor/tayfin-ingestor-api/schemas/*`
- `.github/issues/36/e36-03-task-local-verification-report.md`
- `.github/issues/36/e36-03-task-qa-validation.md`
- `.github/issues/36/e36-03-task-lead-review.md`

Reviewers: @lead-dev, @qa
Labels: docs, epic-36

Checklist for reviewer
- [ ] Examples validated against schema (QA report attached).
- [ ] No secrets committed.
- [ ] Env var tables correct for local dev.

Notes
- This PR is intended as a docs-only change. No code runtime changes included. If you prefer the follow-up items (AR-2..AR-4) to be applied before merge, they are already implemented in this branch (JOB_RUN_ID clarification, validation helper, curl example improvements).
