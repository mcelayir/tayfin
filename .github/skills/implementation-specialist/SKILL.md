---
name: implementation-specialist
description: Skill for learning, testing, and validating new tools via Spikes and documentation.
---

# Skill: Technical Implementation & Validation

## 1. The "Spike" Protocol (Mandatory for New Tools)
When tasked with using a library, package, or API you have not used in this codebase before:
1. **Creation:** Create a dedicated test file at `tests/spikes/test_<tool_name>.py`.
2. **Experimentation:** Implement a minimal working example that covers:
   - Dependency initialization.
   - Core data retrieval/processing.
   - Error handling patterns.
3. **Verification:** Validate the spike against our **"Non-Negotiables"**:
   - Does it use ORM-like patterns (e.g., Active Record)? If so, **REJECT** and notify `@lead-dev`.
   - Does it hold state in a way that breaks idempotency?
4. **Conclusion:** Report to the `@lead-dev` with a summary of findings (e.g., "Tool performs well, adheres to SQLAlchemy Core requirements").

## 2. Documentation Synthesis
If your spike reveals non-obvious performance characteristics, usage quirks, or "gotchas":
1. **Knowledge Capture:** Create a summary in a new file within `docs/knowledge/`.
2. **Linking:** Reference this new knowledge file in the implementation PR.
3. **Feedback Loop:** Tag the `@lead-dev` to suggest an update to the global `docs/knowledge/` index.

## 3. Implementation Guardrails
- **Dependency Management:** Never add a package to `pyproject.toml` without first having the Lead Developer's approval recorded in the associated ADR.
- **Environment Safety:** If the tool requires environment variables or external API keys, ensure they are handled via the approved Tayfin secret management pattern (refer to `docs/knowledge/security/`).
- **Idempotency Check:** Every implementation must ensure that running the code twice on the same input produces the same database state.