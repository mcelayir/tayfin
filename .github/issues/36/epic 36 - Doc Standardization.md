<!--
Epic: Issue #36 — Documentation Standardization
Created: 2026-03-22
Owner: TBD (confirm bounded context owners)
-->
# Epic 36 — Doc Standardization

## Owners & Delegation

- **Owner:** @lead-dev (final review & approval)
- **Implementer / Maintainer:** @dev (produce and maintain READMEs)
- **QA / Validator:** @qa (validation of examples and docs)

Implementation and ongoing maintenance are delegated to `@dev`; `@lead-dev` must review and approve before merge, and `@qa` will validate documentation correctness and examples.

## Objective

Standardize README documentation across top-level modules and submodules in Tayfin to a single, discoverable template so new contributors and cross-team integrations can onboard quickly and consistently.

## Background

Currently README coverage and shape varies between contexts (`tayfin-ingestor`, `tayfin-indicator`, `tayfin-screener`, `tayfin-app`). This epic delivers a canonical README template and per-module README files for jobs and APIs, plus BFF/app integration docs.

## Scope

Includes:
- One top-level `README.md` per module (`tayfin-ingestor`, `tayfin-indicator`, `tayfin-screener`, `tayfin-app`).
- One `README.md` for each submodule that exposes jobs and API surfaces (e.g., `tayfin-ingestor/tayfin-ingestor-jobs/README.md`, `tayfin-ingestor/tayfin-ingestor-api/README.md`).
- BFF integration mapping and setup docs for `tayfin-bff`.

Excludes:
- Code changes, runtime refactors, or feature implementations beyond documentation.

## Definition of Ready (DoR)

All of the following must be true before work begins:

- Product/client confirms epic objective and priority.
- Bounded context owners identified for each module.
- Template specification approved by `@lead-dev` (structure and required sections).
- Access to code and example payloads available for creating realistic examples.

## Definition of Done (DoD)

All of the following must be completed and verified before the epic is accepted:

- Canonical README template committed under `.github/README_TEMPLATES/README_MODULE.md`.
- Per-module and per-submodule `README.md` files created and placed in the respective folders.
- Each README contains: Service Overview, Local Execution & Jobs, Environment Variables, Execution Examples, API Reference with request/response examples, and curl example.
- Realistic request/response payloads derived from code or tested against local dev stacks.
- PRs opened for each module with required reviewers from owning context and `@lead-dev` tagged.
- QA validation tasks created and passed (see Acceptance Criteria below).
- No secrets or credentials committed; security review performed if docs include auth examples.
- Documentation reviewed and merged.

## Milestones

1. Approve template and DoR (triage).  
2. Generate READMEs (per-module and per-submodule).  
3. Technical review (`@lead-dev`).  
4. QA validation (`@qa`).  
5. PRs merged and release notes updated.

## Acceptance Criteria

- Template approved and accessible in the repo.  
- For each top-level module, a `README.md` exists and follows the template.  
- For each jobs and api submodule, a `README.md` exists with at least one realistic example payload.  
- BFF doc maps endpoints and aggregation flows for `tayfin-bff`.  
- QA checklist items pass: documentation completeness, examples run locally, and API curl commands return expected (mocked or local) responses.

## Tasks

All tasks below are written as discrete, reviewable steps. Tasks marked Sequential must be completed in order; Parallel tasks can be worked on concurrently once the template is approved.

| ID | Title | Description | Expected output | Sequence | Dependencies |
| --: | :--- | :--- | :--- | :---: | :--- |
| E36-01 | Triage & Ownership Confirmation | Confirm bounded-context owners for `ingestor`, `indicator`, `screener`, `app` and designate reviewers (`@lead-dev`, `@qa`). | List of owners and reviewers added to issue and PR template. | Sequential | None |
| E36-02 | Approve README Template (Design) | Create canonical README template matching Issue #36 spec (Service Overview, Local Execution & Jobs, Env vars table, Execution examples, API Reference, curl example). | ` .github/README_TEMPLATES/README_MODULE.md` draft PR. | Sequential | E36-01 |
| E36-03 | Populate `tayfin-ingestor` READMEs | Produce `tayfin-ingestor/README.md`, `tayfin-ingestor/tayfin-ingestor-api/README.md`, `tayfin-ingestor/tayfin-ingestor-jobs/README.md` using realistic examples from code. | 3 README files committed in `tayfin-ingestor` path. | Parallel | E36-02 |
| E36-04 | Populate `tayfin-indicator` READMEs | Produce top-level and submodule READMEs for `tayfin-indicator` with examples. | 3 README files (top-level + api + jobs) committed. | Parallel | E36-02 |
| E36-05 | Populate `tayfin-screener` READMEs | Produce top-level and submodule READMEs for `tayfin-screener` with examples. | 3 README files committed. | Parallel | E36-02 |
| E36-06 | Populate `tayfin-app` & `tayfin-bff` READMEs | Document architecture positioning, setup guide, and API mapping for `tayfin-bff` and `tayfin-app`. | `tayfin-app/README.md`, `tayfin-bff/README.md` committed. | Parallel | E36-02 |
| E36-07 | Internal Technical Review | `@lead-dev` reviews template and per-module docs, requests changes, and approves. | Review comments resolved, approvals recorded. | Sequential | E36-03, E36-04, E36-05, E36-06 |
| E36-08 | QA Validation Tasks | `@qa` creates validation tasks (docs smoke tests, example curl commands, run job examples) and executes them. | QA task list and validation results attached to issue. | Sequential | E36-07 |
| E36-09 | Finalize PRs & Merge | Open/aggregate PRs, tag reviewers, address final comments, merge to main. | PRs merged. | Sequential | E36-08 |
| E36-10 | Release Notes & Announce | Add a short release note describing documentation updates and notify teams. | Release note entry and Slack/GitHub announcement. | Sequential | E36-09 |

## Parallelization Guidance

- After E36-02 (template approval), tasks E36-03, E36-04, E36-05, and E36-06 can be executed in parallel by separate contributors.
- Reviews (E36-07) should wait until initial drafts for all modules exist, but reviews may be assigned in parallel across reviewers.

## Risks & Mitigations

- Risk: Inaccurate example payloads — Mitigation: flag examples as "derived from code" and request confirmation from context owner; QA to validate against local stacks.  
- Risk: Secret leakage in examples — Mitigation: scrub values and use placeholder tokens; security review prior to merge.

## Next Steps (for me / you)

1. Confirm owners for each bounded context so I can update DoR and assign reviewers.  
2. Approve the canonical template or request changes.  
3. After approval, ask `@lead-dev` to break down the work into implementation tasks and `@qa` to prepare validation tasks.

---

If you confirm owners and approve this epic, I will mark the epic file as complete and hand off to `@lead-dev` for task breakdown.
