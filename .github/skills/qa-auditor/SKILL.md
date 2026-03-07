---
name: qa-auditor
description: Tools for technical auditing, mathematical validation, and architectural compliance.
---

# Skill: Technical Audit & Quality Validation

## 1. Static Analysis & Compliance Audit
- **Dependency Scan:** Audit `pyproject.toml` and imports. If an ORM or unauthorized library is detected, flag `ARCH_BLOCKER`.
- **Context Integrity:** Use `grep` or AST analysis to ensure no cross-context database access exists. Every interaction with another context must involve an HTTP/API call.
- **ADR Compliance:** Compare the PR/Commit message against the referenced ADR in `docs/architecture/adr/`. If the implementation diverges from the ADR, flag `ADR_MISMATCH`.

## 2. Mathematical & Algorithmic Verification
- **Indicator Validation:** If the task involves an indicator (e.g., SMA, VCP), run the provided `tests/spikes/test_<indicator>.py` and compare results against the reference research spec in `docs/research/`.
- **Idempotency Test:** Execute the code twice in a local environment. Compare `job_run_id` and database state. If state changes on the second run, flag `IDEMPOTENCY_FAILURE`.

## 3. Reporting Protocols
When a validation fails, provide a "Quality Audit Report" to the `@developer` with:
- **Violation Type:** (e.g., `ARCH_BLOCKER`, `MATH_ERROR`, `IDEMPOTENCY_FAILURE`)
- **Reference:** The file/line that violates the constraint.
- **Mitigation:** The required fix to bring it back to compliance.

## 4. Final Sign-off Protocol
- Only issue a `PASS` verdict once:
    1. Static analysis is clean.
    2. ADR compliance is verified.
    3. Math/Indicator results match research specs.
    4. Code coverage is confirmed (>= 80% for new logic).