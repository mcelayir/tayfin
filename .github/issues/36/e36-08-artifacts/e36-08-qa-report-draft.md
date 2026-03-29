# E36-08 QA Report (draft)

Generated: 2026-03-29
Branch: `docs/issue-36/st-01-placeholders`

Summary
-------
I ran a set of QA checks and saved artifacts under `.github/issues/36/e36-08-artifacts/`.

Completed tasks (artifacts produced)
-----------------------------------
- E36-08.1 Docs smoke tests: per-README logs and summary (`.github/issues/36/e36-08-artifacts/docs-smoke-*.txt` and `docs-smoke-summary.txt`).
- E36-08.5 Re-run validators: `indicator-validator.json`, `screener-validator.json`, `bff-validator.json`.
- E36-08.6 Security scan: `security-scan.txt`.
- E36-08.2 BFF curl attempt: `curl-bff-dashboard.json` and `curl-bff-dashboard.err` (network unreachable; see notes).

Notes & Blockers
-----------------
- BFF endpoint `http://localhost:8080/v1/bff/mcsa/dashboard` was not reachable from this environment (HTTP code captured as `000`). If you want me to actually exercise curl examples, please confirm whether there is a local BFF running or if you want me to start a local mock.
- I did not run job examples or start the UI dev server. These are potentially long-running and may require local services (databases, upstream APIs). Please confirm if you want me to run them here; I will proceed if you give permission.

Next steps
----------
- Confirm whether to (A) run job examples now, and (B) start the UI dev server to validate E36-08.3 and E36-08.4.
- If you prefer, I can attach these artifacts to PR #39 and tag `@qa` and `@lead-dev` for further action.

Artifacts
---------
List of artifacts created:

```
.github/issues/36/e36-08-artifacts/
  docs-smoke-summary.txt
  docs-smoke-*.txt
  indicator-validator.json
  screener-validator.json
  bff-validator.json
  security-scan.txt
  curl-bff-dashboard.json
  curl-bff-dashboard.err
```
