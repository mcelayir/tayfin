<!--
Task breakdown for E36-04 — Populate `tayfin-indicator` READMEs
Created: 2026-03-22
Owner: @dev
--> 
# E36-04 Task Breakdown — `tayfin-indicator` READMEs

Instruction: implementers should follow the canonical template at `.github/README_TEMPLATES/README_MODULE.md`. Each task below is small, reviewable, and has a clear output that can be verified by `@lead-dev` and `@qa`.

| ID | Name | Definition | Output |
| --: | :--- | :--- | :--- |
| E36-04.1 | Collect artifacts & references | Locate code files, API handlers, indicator implementations, job scripts, tests, and any existing docs for `tayfin-indicator`. Record authoritative schema/model locations and example payloads. | `tayfin-indicator/artifacts.md` listing repo-relative paths to source, indicator math, example inputs/outputs, tests, and any existing schemas. |
| E36-04.2 | Draft top-level `tayfin-indicator/README.md` | Create the top-level README from the canonical template. Provide module purpose, quick start, links to submodule READMEs, and observability notes. | `tayfin-indicator/README.md` draft committed to branch. |
| E36-04.3 | Draft API README (`tayfin-indicator-api`) | Document endpoints exposed by the indicator API (if present): request/response examples, parameter descriptions, and curl examples. Link to code-models or add inline JSON Schema for outputs where applicable. | `tayfin-indicator/tayfin-indicator-api/README.md` with endpoint docs, schema links, and curl examples. |
| E36-04.4 | Draft Jobs README (`tayfin-indicator-jobs`) | Document indicator calculation jobs, CLI usage, config files, env vars, and example outputs. Include backfill patterns and tuning knobs. | `tayfin-indicator/tayfin-indicator-jobs/README.md` with job list, run commands, and QA checklist. |
| E36-04.5 | Populate Env var details & examples | For all indicator READMEs add env var rows (Type, Default, Example, Notes) and clearly document provenance `JOB_RUN_ID` usage for any DB writes. | ENV tables completed in each README and a short note on provenance usage. |
| E36-04.6 | Add validation metadata header | Add the machine-checkable YAML header to each README: `template_version`, `module`, `owner`, `qa_checklist: true` (unless owner explicitly opts out). | Each new README starts with the YAML header filled. |
| E36-04.7 | Add realistic payloads & schema links | Extract canonical input/output shapes from indicator implementations (e.g., VCP outputs, SMA series), provide JSON Schema files under `tayfin-indicator/.../schemas/` or link to model code. Mark unvalidated examples as `illustrative`. | JSON Schema files or repo-code links added; example payloads present and labeled. |
| E36-04.8 | Local verification & QA readiness | Validate example payloads against schema files (using `jsonschema`), run representative CLI jobs locally (with small test datasets) and capture outputs or note blockers. | `.github/issues/36/e36-04-task-local-verification-report.md` with commands run and outputs or notes. |
| E36-04.9 | Open PR and request reviews | Open a single PR for `tayfin-indicator` README changes, tag `@lead-dev` and `@qa`, and reference epic 36. | PR URL and summary added to the issue. |
| E36-04.10 | Address review feedback & finalize | Resolve comments from technical and QA reviewers, update READMEs, and merge when approved. | Final merged PR and issue updated with link to merged changes. |

## Implementation notes

- Follow the exact section ordering from the canonical template.  
- Prefer authoritative shapes discovered in code (indicator implementations, serializers) to craft examples.  
- Keep examples small and executable — prefer `curl` for APIs and one-line job commands for jobs.  
- Do not include secrets; use placeholders like `${API_TOKEN}` or `REDACTED`.  
- When a calculation produces derived numeric outputs (e.g., scores, signal flags), document expected ranges and units.

---

After completing these tasks, mark E36-04 as done in the epic and notify `@qa` to start validations.
