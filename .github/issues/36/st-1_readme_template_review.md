<!--
Review: st-1 — README module template
Source: .github/README_TEMPLATES/README_MODULE.md
Created: 2026-03-22
Reviewer: @dev (draft)
-->
# st-1 README Template Review

## Executive Summary

The canonical template is a strong starting point: it covers Description, Getting Started, Env vars, Execution examples, Jobs, API examples, Observability, Security, QA checklist, and Troubleshooting. It is clear, concise, and easy for contributors to follow. A few gaps and improvements will make it actionable, machine-checkable, and safer to publish.

## Findings (what's good)

- Clear section ordering matching Issue #36 requirements.  
- Includes example request/response and curl usage — good for quick validation.  
- QA checklist present to guide `@qa`.  
- Observability and security sections remind implementers to include metrics and avoid secrets.

## Issues & Risks (what to fix)

1. Placeholders: many `{{...}}` placeholders exist and need precise guidance (allowed values, naming conventions).  
2. Missing strict schema guidance: template suggests examples but doesn't require JSON Schema or link-to-code for request/response types.  
3. No automated validation: repo lacks a machine-checkable checklist or lightweight linter to ensure required sections exist.  
4. Env var table minimal: lacks types, default values, and where/how they are used.  
5. Auth examples: curl uses Bearer token but no explicit guidance on scopes or secure handling (avoid copy-paste of real tokens).  
6. CHANGELOG guidance: no format or required entries described (date, author, summary).  

## Recommendations (high level)

- Replace generic `{{placeholders}}` with explicit examples and rules in a short guidance block inside the template.  
- Add requirement to include either a JSON Schema file or a link to the code model for each API endpoint.  
- Add a CI-checkable README checklist (file header YAML or simple grepable anchors).  
- Expand Env var table to include Type, Default, Example, and Notes.  
- Add a security note showing how to test auth locally (using short-lived test tokens or dev-only flags).  
- Specify CHANGELOG entry format and example.

## Actionable Steps

Below are suggested tasks to finish the template and prepare implementation work. Each task is small and reviewable.

| ID | Task | Description | Owner | Parallelizable |
| --: | :--- | :--- | :--- | :---: |
| ST-01 | Flesh out placeholders guidance | Add a short "How to fill placeholders" subsection to the template describing naming rules and examples for `{{module}}`, `{{service_name}}`, `{{repo_path}}`, and `{{job_run_id}}`. | @dev | Yes |
| ST-02 | Require API schema linkage | Update template to require either an inline JSON Schema or a link to the canonical model/type in code (path + line). Provide example. | @dev | Yes |
| ST-03 | Expand Env var table | Add columns `Type`, `Default`, `Example`, `Notes` to the template's Env var table and show one fully populated example. | @dev | Yes |
| ST-04 | Add README validation hint | Add a machine-checkable header (YAML or HTML comment) with keys: `template_version`, `module`, `owner`, `qa_checklist:true`. Implementers fill these so CI can validate presence. | @dev / @lead-dev | Yes |
| ST-05 | Add auth & testing guidance | Add short guidance for local auth testing and explicit note to never include real credentials. | @dev | Yes |
| ST-06 | Define CHANGELOG format | Add a small subsection with required fields for CHANGELOG entries and an example. | @dev | Yes |
| ST-07 | Draft repo CI job (optional) | Create a small CI job (e.g., GitHub Action) that verifies required anchors exist and that JSON fences are valid JSON. Provide a follow-up issue for implementation. | @dev | No (depends on ST-04) |
| ST-08 | Lead review | Ask `@lead-dev` to review the updated template and approve. | @lead-dev | No |
| ST-09 | QA validation plan | Ask `@qa` to prepare validation tasks that will run curl examples and job steps in a local test environment. | @qa | No |

## Minimal Edits I Can Make (if you want)

- Insert a small "Placeholder Guidance" subsection into the template (low risk).  
- Add the machine-checkable YAML header example.  

Tell me if you want me to apply ST-01 and ST-04 now; I can patch the template and create a follow-up issue or PR draft. Otherwise, mark ST-08 and ST-09 as next steps to request reviews.
