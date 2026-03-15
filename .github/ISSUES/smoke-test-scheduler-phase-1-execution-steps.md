Step 1:
I executed
`docker compose -f infra/docker-compose.yml --env-file .env up --build --remove-orphans`

I observed that most of the jobs ran however between jobs there is race condition. All jobs starts more or less together. This makes vcp job run before the ingestion jobs are done. 

Logs of execution is in the smoke-test-scheduler-phase-1-scheduler-container-logs.md file

What new need to do is to change this in a way that jobs for each module groupped and running in sequential way. First ingestor jobs, then indicator jobs then screener jobs.

@lead-dev. Create the next tasks to implement the sequential workflow on the scheduler.

- **Project description:** `docs/architecture/tayfin_project_documentation.md`
- **Architecture Laws:** `docs/architecture/ARCHITECTURE_RULES.md`
- **ADRs (Architecture Decision Records):** `docs/architecture/adr/*`
- **Tech Stack & Tooling:** `docs/architecture/TECH_STACK_RULES.md`
- **Tooling Knowledge Base:** `docs/knowledge/*`
- **Coding Style:** `docs/architecture/CODEBASE_CONVENTIONS.md`
- **Planning Protocol:** `docs/ai/COPILOT_TASK_PLANNING_GUIDE.md`

Provide the breakdown to this chat. Use a structured format. Use tabular format when possible.