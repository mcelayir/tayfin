<!--
Task breakdown for E36-06 — Populate `tayfin-app` & `tayfin-bff` READMEs
Created: 2026-03-29
Owner: @dev
-->
# E36-06 Task Breakdown — `tayfin-app` & `tayfin-bff` READMEs

Instruction: implementers must follow the canonical template at `.github/README_TEMPLATES/README_MODULE.md`. Each task below is small, reviewable, and has a clear output that can be validated by `@lead-dev` and `@qa`.

| ID | Name | Definition | Output |
| --: | :--- | :--- | :--- |
| E36-06.1 | Collect artifacts & references | Locate BFF and App code, API routes, BFF aggregation mappings, UI startup scripts, deployment config, and any existing docs. Record authoritative schema/model locations and example requests/responses. | `tayfin-app/artifacts.md` and `tayfin-bff/artifacts.md` listing repo-relative paths to source, routes, UI entry points, example inputs/outputs, and tests. |
| E36-06.2 | Draft top-level `tayfin-app/README.md` | Create the top-level README from the canonical template covering purpose, architecture positioning, and integration points. | `tayfin-app/README.md` draft committed to branch. |
| E36-06.3 | Draft `tayfin-bff/README.md` | Document BFF responsibilities, exposed endpoints, aggregated payload shapes, config and example curl requests that show how clients should call the BFF. | `tayfin-bff/README.md` with endpoints, example requests/responses, and schema links. |
| E36-06.4 | Draft App (UI) README | Document how to run the UI, build steps, local dev proxy to the BFF, environment variables, and common troubleshooting items. | `tayfin-app/tayfin-ui/README.md` with run/build instructions and quick dev workflow. |
| E36-06.5 | Populate Env var details & examples | For all READMEs add env var rows (Type, Default, Example, Notes) and clearly document authentication patterns (if any) and secrets management. | ENV tables completed in each README and a short note on secrets handling. |
| E36-06.7 | Add realistic payloads & schema links | Extract canonical request/response shapes from BFF route handlers and UI contracts; add JSON Schema files under `tayfin-bff/schemas/` or link to model code. | JSON Schema files or code links added; example payloads present and labeled (`examples/`). |
| E36-06.8 | Local verification & QA readiness | Validate example payloads against schema files (using `jsonschema`), run the UI locally with a mocked BFF or local BFF to ensure examples are runnable, and capture outputs or note blockers. | `.github/issues/36/e36-06-task-local-verification-report.md` with commands run and outputs or blockers. |

## Implementation notes

- Follow the canonical template ordering and keep examples small and executable.
- Bounded-context guardrail: `tayfin-app` and `tayfin-bff` MUST NOT read other contexts' databases; BFF may call internal APIs (indicator, screener, ingestor) only via HTTP clients.
- Prefer authoritative shapes discovered in code (BFF serializers, UI props) to craft examples. When shapes are ambiguous, mark examples as `illustrative` and request owner confirmation.
- For UI examples, include the minimal proxy config to point the dev server at a local BFF endpoint.

## Standard task template (for each subtask)

Title

Goal

What Must Be Implemented

Constraints

Validation Steps

Commit Requirements

Example (E36-06.3)

Title

E36-06.3 — Draft `tayfin-bff/README.md`

Goal

Document BFF endpoints, aggregation contracts, and example calls so frontend and integrators know how to retrieve composed data.

What Must Be Implemented

- `tayfin-bff/README.md` with:
  - service overview and responsibilities
  - endpoint table (`/v1/bff/<resource>`), request params, and response examples
  - schema links to `tayfin-bff/schemas/`
  - quick curl examples using `TAYFIN_BFF_BASE_URL`

Constraints

- Use repo-wide README template.
- BFF must not read other contexts' DBs; call upstream APIs over HTTP.

Validation Steps

1. Run local BFF (if a runnable entry point exists) with env vars from README examples.
2. Curl the documented endpoints and compare responses to example JSON (or run validator script against schemas).

Commit Requirements

- Commit message: `docs(bff): add README (E36-06.3)`
- Push to epic branch and open PR per epic instructions.

---

After completing these tasks, mark E36-06 as done in the epic and notify `@qa` to start validations.
