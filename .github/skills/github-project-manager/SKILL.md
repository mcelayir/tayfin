---
name: github-project-manager
description: Tools for interacting with GitHub Projects, Issues, and PRs via API.
---

# Skill Instructions

## 1. Capabilities
You are authorized to perform the following operations using the GitHub API:
- **Project Items:** List, move, and update items on a project board.
- **Issues:** Create, update bodies, change labels, and assignees.
- **Comments:** Post updates on issues to notify the `@lead-dev`.

## 2. Operational Procedures

### Task Breakdown
When asked to break down an issue or epic:
1. Fetch the existing issue details.
2. Use `docs/ai/COPILOT_TASK_PLANNING_GUIDE.md` to format the implementation plan.
3. Apply the plan to the issue body.
4. Add a comment: "@lead-dev: Implementation plan drafted for review."

### Status Updates
When moving items (e.g., "To Do" to "In Progress"):
1. Confirm the new state is valid according to Tayfin's workflow.
2. Update the project item field.
3. Post a comment: "Status updated to [NEW_STATUS]. Handoff to [ROLE]."

## 3. Safety & Governance
- **API Limits:** If you encounter rate limits, wait and retry with exponential backoff.
- **Traceability:** Every action that modifies data MUST be recorded with a comment or linked to a `job_run_id` if applicable.
- **No Overrides:** Never bypass status transitions; if a move is invalid (e.g., "Done" to "In Progress" without re-opening), ask the user for confirmation.
- **Context Awareness:** Ensure all project items link back to their parent Epic/Issue to maintain a clear audit trail.