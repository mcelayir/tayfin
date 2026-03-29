<!--
Task breakdown for E36-05 — Populate `tayfin-screener` READMEs
Created: 2026-03-29
Owner: @dev
-->
# E36-05 Task Breakdown — `tayfin-screener` READMEs

Instruction: implementers must follow the canonical template at `.github/README_TEMPLATES/README_MODULE.md`. Each task below is small, reviewable, and has a clear output that can be validated by `@lead-dev` and `@qa`.

| ID | Name | Definition | Output |
| --: | :--- | :--- | :--- |
| E36-05.1 | Collect artifacts & references | Locate code files, API handlers, screening algorithms, job scripts, tests, and any existing docs for `tayfin-screener`. Record authoritative schema/model locations and example payloads. | `tayfin-screener/artifacts.md` listing repo-relative paths to source, screening rules, example inputs/outputs, tests, and any existing schemas. |
| E36-05.2 | Draft top-level `tayfin-screener/README.md` | Create the top-level README from the canonical template. Provide module purpose, quick start, links to submodule READMEs, and observability notes. | `tayfin-screener/README.md` draft committed to branch. |
| E36-05.3 | Draft API README (`tayfin-screener-api`) | Document endpoints exposed by the screener API (if present): request/response examples, parameter descriptions, and curl examples. Link to code-models or add inline JSON Schema for outputs where applicable. | `tayfin-screener/tayfin-screener-api/README.md` with endpoint docs, schema links, and curl examples. |
| E36-05.4 | Draft Jobs README (`tayfin-screener-jobs`) | Document screening jobs, CLI usage, config files, env vars, and example outputs. Include scheduling/backfill patterns and tuning knobs. | `tayfin-screener/tayfin-screener-jobs/README.md` with job list, run commands, and QA checklist. |
| E36-05.5 | Populate Env var details & examples | For all screener READMEs add env var rows (Type, Default, Example, Notes) and clearly document provenance `JOB_RUN_ID` usage for any DB writes. | ENV tables completed in each README and a short note on provenance usage. |
| E36-05.7 | Add realistic payloads & schema links | Extract canonical input/output shapes from screening code (e.g., screener result shape), provide JSON Schema files under `tayfin-screener/.../schemas/` or link to model code. Mark unvalidated examples as `illustrative`. | JSON Schema files or repo-code links added; example payloads present and labeled. |
| E36-05.8 | Local verification & QA readiness | Validate example payloads against schema files (using `jsonschema`), run representative CLI jobs locally (with small test datasets) and capture outputs or note blockers. | `.github/issues/36/e36-05-task-local-verification-report.md` with commands run and outputs or notes. |

## Implementation notes

- Follow the canonical template ordering and keep examples small and executable.  
- Prefer authoritative shapes discovered in code (screener algorithms, serializers) to craft examples.  
- For screening outputs, document the meaning and range of score fields, flags, and thresholds used by rules.  
- Keep environment-variable recommendations consistent with other modules (`POSTGRES_*`, `JOB_RUN_ID`, `TAYFIN_CONFIG_DIR`, timeouts).  
- Mark any examples that are illustrative and request owner confirmation where needed.

---

After completing these tasks, mark E36-05 as done in the epic and notify `@qa` to start validations.
