# Tayfin Project Constitution

## 1. Project Overview
Tayfin is a local-first, high-discipline financial analysis suite. It is designed to ingest market data, compute technical indicators (like VCP, SMA, ATR), and provide screening tools for traders.

## 2. Bounded Context Architecture
We follow a strict bounded-context separation. Each folder is a sovereign domain:
- `tayfin-ingestor`: Raw market data ownership.
- `tayfin-indicator`: Derived mathematical indicators.
- `tayfin-screener`: Algorithmic scanning (VCP, etc.).
- `tayfin-app`: The UI and BFF.

## 3. Mandatory Rules & Standards (READ THESE FIRST)
Every action you take MUST align with the established project laws found here:
- **Project description:** `docs/architecture/tayfin_project_documentation.md`
- **Architecture Laws:** `docs/architecture/ARCHITECTURE_RULES.md`
- **ADRs (Architecture Decision Records):** `docs/architecture/adr/*`
- **Tech Stack & Tooling:** `docs/architecture/TECH_STACK_RULES.md`
- **Tooling Knowledge Base:** `docs/knowledge/*`
- **Coding Style:** `docs/architecture/CODEBASE_CONVENTIONS.md`
- **Planning Protocol:** `docs/ai/COPILOT_TASK_PLANNING_GUIDE.md`

## 4. Technical Non-Negotiables
- **DB:** Use SQLAlchemy Core ONLY. No ORM.
- **CLI:** All jobs must be Typer apps.
- **Communication:** Cross-context access is via HTTP APIs only. Never read another context's database.
- **Provenance:** Every write must be linked to a `job_run_id`.

## 5. Specialist Agents
For specific tasks, you may refer to the personas in `.github/agents/`. Each agent is empowered with specific Skills located in `.github/skills/`.

## 6. Maintenance Responsibility
**Note to all agents:** It is the explicit role of the **Lead Developer** to keep this `copilot-instructions.md` file updated and accurate. If you detect that our project laws have evolved, notify the Lead Developer immediately.