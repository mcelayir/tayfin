<!--
Task breakdown for E36-07 — Internal Technical Review
Created: 2026-03-29
Owner: @lead-dev
-->
# E36-07 Task Breakdown — Internal Technical Review

Instruction: The lead developer must review, validate, and, if necessary, request fixes for all documentation and schema/example artifacts produced in Issue #36. Each task below is discrete, reviewable, and must be completed for all relevant modules before QA and merge.

| ID         | Name                                 | Definition                                                                                  | Output                                                                                       |
| ---------- | ------------------------------------ | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| E36-07.1   | Review ingestor documentation        | Review `tayfin-ingestor/README.md`, API/jobs READMEs, schemas, and example payloads.         | Review comments, approval, or change requests recorded in PR.                                |
| E36-07.2   | Review indicator documentation       | Review `tayfin-indicator/README.md`, API/jobs READMEs, schemas, and example payloads.        | Review comments, approval, or change requests recorded in PR.                                |
| E36-07.3   | Review screener documentation        | Review `tayfin-screener/README.md`, API/jobs READMEs, schemas, and example payloads.         | Review comments, approval, or change requests recorded in PR.                                |
| E36-07.4   | Review app & BFF documentation       | Review `tayfin-app/README.md`, `tayfin-bff/README.md`, UI README, schemas, and examples.     | Review comments, approval, or change requests recorded in PR.                                |
| E36-07.5   | Validate schema/example correctness  | For each module, verify that example payloads conform to their JSON Schemas using validator scripts. | Validation results or issues posted as PR comments or review artifacts.                      |
| E36-07.6   | Check template & section compliance  | Ensure all READMEs follow the canonical template and required sections are present.          | Checklist or summary comment in PR.                                                          |
| E36-07.7   | Security & secrets review            | Confirm no secrets, credentials, or sensitive data are present in docs or examples.          | Security review comment or checklist in PR.                                                  |
| E36-07.8   | Approve or request changes           | Approve PR if all criteria are met, or request changes with specific feedback.               | PR approval or change request.                                                               |

## Implementation notes

- Use the canonical template at `.github/README_TEMPLATES/README_MODULE.md` as the compliance baseline.
- For each module, check that:
  - All required README sections are present and populated.
  - Example payloads are realistic and validated against schemas.
  - Environment variable tables are complete and accurate.
  - API/curl examples are runnable or clearly marked as illustrative.
- Run the provided validator scripts for each module and review outputs.
- If any issues are found, leave detailed review comments and assign to the relevant implementer.
- Confirm that no secrets or credentials are present in any committed files.
- Approve the PR only when all review criteria are satisfied.

## Validation Steps

1. Open the PR and review all changed files for each module.
2. Run validator scripts and check outputs for each module.
3. Confirm template compliance and documentation completeness.
4. Perform a security review for secrets or sensitive data.
5. Record review results and either approve or request changes.

## Commit Requirements

- Commit message: `docs(epic-36): add E36-07 lead review task breakdown`
- Place this file at `.github/issues/36/e36-07-task-breakdown.md`.
- Notify `@lead-dev` to begin review upon completion of E36-06.
