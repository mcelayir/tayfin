<!--
Task breakdown for E36-08 — QA Validation Tasks
Created: 2026-03-29
Owner: @qa
-->
# E36-08 Task Breakdown — QA Validation Tasks

Instruction: The QA lead must execute the validation and smoke-test tasks listed below for all modules (ingestor, indicator, screener, app/BFF). Each task is discrete, reproducible, and should produce an artifact (logs, command outputs, or a short report) attached to the issue/PR.

| ID         | Name                           | Definition                                                                                         | Output                                                                                             |
| ---------- | ------------------------------ | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| E36-08.1   | Run docs smoke tests           | Verify READMEs render, links resolve, and required sections exist for each module's README.       | `e36-08/docs-smoke-<module>.txt` logs and pass/fail summary attached to issue.                    |
| E36-08.2   | Run example curl commands      | Execute documented curl examples (BFF endpoints, API examples) against local/mocked endpoints.     | `e36-08/curl-outputs-<module>.txt` with request/response pairs and notes for any mismatches.      |
| E36-08.3   | Run job examples locally       | Run at least one representative job (Typer) per context where feasible using example env vars.     | `e36-08/job-run-<module>.txt` with stdout/stderr and success/failure status.                       |
| E36-08.4   | Run UI with mocked BFF         | Start `tayfin-ui` dev server with dev proxy pointing to a local/mocked BFF; confirm key views load. | `e36-08/ui-dev-run.txt` and screenshots or brief notes on rendered pages (or blockers).           |
| E36-08.5   | Re-run validators & compare    | Re-run JSON Schema validators for indicator, screener, and BFF and compare results to prior run.   | `e36-08/validator-recheck.json` and a short delta summary noting any failures or warnings.         |
| E36-08.6   | Security & secrets verification | Scan changed files for secrets, credentials, or accidental tokens (grep for common patterns).       | `e36-08/security-scan.txt` and any remediation requests or confirmations.                          |
| E36-08.7   | QA report and attach to PR     | Compile the artifacts above into a concise QA report and attach to PR #39 and the epic issue.      | `e36-08/e36-08-qa-report.md` and PR comment tagging `@lead-dev` and `@dev` with links to artifacts. |

## Implementation notes

- Use branch: `docs/issue-36/st-01-placeholders` for all validation checks.
- Prefer local mocks where full integration isn't possible; mark any external dependency as a blocker in the report.
- Keep commands and env values non-sensitive; use placeholders for secrets.
- Store artifacts under `.github/issues/36/e36-08-artifacts/` and reference them in the final QA report.

## Validation Steps (example)

1. Clone branch and ensure Python venv is active.
2. Run validator scripts:

```bash
python3 tayfin-indicator/tayfin-indicator-api/scripts/validate_examples.py > .github/issues/36/e36-08-artifacts/indicator-validator.json
python3 tayfin-screener/tayfin-screener-api/scripts/validate_examples.py > .github/issues/36/e36-08-artifacts/screener-validator.json
python3 tayfin-app/tayfin-bff/scripts/validate_examples.py > .github/issues/36/e36-08-artifacts/bff-validator.json
```

3. Run curl examples (replace `TAYFIN_BFF_BASE_URL` with `http://localhost:8080` or mocked URL):

```bash
curl -s -X GET "$TAYFIN_BFF_BASE_URL/v1/bff/mcsa/dashboard" -H "Accept: application/json" > .github/issues/36/e36-08-artifacts/curl-bff-dashboard.json
```

4. Run a sample job (example):

```bash
TAYFIN_CONFIG_DIR=./config JOB_RUN_ID=test-run python3 tayfin-ingestor/tayfin-ingestor-jobs/scripts/run_example_job.py > .github/issues/36/e36-08-artifacts/ingestor-job.txt
```

5. Run UI dev with proxy (example):

```bash
cd tayfin-app/tayfin-ui
npm install
TAYFIN_BFF_BASE_URL=http://localhost:8080 npm run dev
```

6. Run security scan (simple grep):

```bash
grep -R "AKIA\|SECRET\|PASSWORD\|TOKEN\|BEGIN RSA" -n . | sed -n '1,200p' > .github/issues/36/e36-08-artifacts/security-scan.txt || true
```

## Commit Requirements

- Place artifacts under `.github/issues/36/e36-08-artifacts/` and the QA report at `.github/issues/36/e36-08-artifacts/e36-08-qa-report.md`.
- Commit message: `docs(epic-36): add E36-08 QA task breakdown and artifact placeholders`
- Notify `@qa` and `@lead-dev` when artifacts are attached to the PR.
