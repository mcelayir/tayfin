<!--
Task breakdown for E36-03 — Populate `tayfin-ingestor` READMEs
Created: 2026-03-22
Owner: @dev
-->
# E36-03 Task Breakdown — `tayfin-ingestor` READMEs

Instruction: implementers should follow the canonical template at `.github/README_TEMPLATES/README_MODULE.md`. Each task below is small, reviewable, and has a clear output that can be verified by `@lead-dev` and `@qa`.

| ID | Name | Definition | Output |
| --: | :--- | :--- | :--- |
| E36-03.1 | Collect artifacts & references | Locate code, API handlers, job scripts, existing docs and example payloads for `tayfin-ingestor`. Record paths and any existing schemas. | A short `artifacts.md` listing repo-relative paths to: API handlers, job scripts, schemas, and example data. |
| E36-03.2 | Draft top-level `tayfin-ingestor/README.md` | Create the top-level README using the canonical template. Provide Service Overview, Getting Started, links to submodule READMEs. | `tayfin-ingestor/README.md` draft committed to branch. |
| E36-03.3 | Draft API README (`tayfin-ingestor-api`) | Document endpoints, include schema links or inline JSON Schemas, request/response examples, and curl commands. Use realistic examples from code where possible. | `tayfin-ingestor/tayfin-ingestor-api/README.md` with endpoint table, schema references, and curl examples. |
| E36-03.4 | Draft Jobs README (`tayfin-ingestor-jobs`) | Document available jobs/cron, env vars required for jobs, execution examples and local run commands. Include sample output or logs if possible. | `tayfin-ingestor/tayfin-ingestor-jobs/README.md` with job list, cron examples, and run instructions. |
| E36-03.5 | Populate Env var details & examples | For all READMEs add env var rows (Type, Default, Example, Notes) and call out `JOB_RUN_ID` usage. | ENV tables completed in each README and a short note on provenance usage. |
| E36-03.6 | Add validation metadata header | Add the machine-checkable YAML header to each README: `template_version`, `module`, `owner`, `qa_checklist: true`. | Each README starts with the YAML/HTML header filled. |
| E36-03.7 | Add realistic payloads & schema links | Where inline examples are used, prefer JSON Schema or code-model links. Mark unverified examples as `illustrative`. | JSON Schema files linked or inline; example payloads present and labeled. |
| E36-03.8 | Local verification & QA readiness | Run curl examples against local dev or mocked endpoints and run job examples; capture outputs and any deviations. | A `verification.md` with commands run and captured outputs (or notes if local run not possible). |
| E36-03.9 | Open PR and request reviews | Create a single PR for the `tayfin-ingestor` README changes, tag `@lead-dev` and `@qa`, and reference epic 36. | PR URL and summary added to the issue. |
| E36-03.10 | Address review feedback & finalize | Resolve reviewer comments, update READMEs, and merge when approved. | Final merged PR and issue updated with link to merged changes. |

## Implementation notes

- Follow the exact section ordering from the canonical template.  
- Keep examples small and executable — prefer `curl` and one-line job commands.  
- Do not include secrets; use placeholder tokens.  
- Mark any assumptions or open questions in the PR description so `@lead-dev` can triage.  

---

After you complete these tasks, mark E36-03 as done in the epic and notify `@qa` to start validations.
