<!--
Artifacts inventory for `tayfin-app` (E36-06.1)
Generated: 2026-03-29
Owner: @dev
-->
# tayfin-app artifacts

Top-level components and notable files discovered in the `tayfin-app` context:

- `tayfin-app/tayfin-ui/` (React/Vite UI)
  - `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`
  - `src/` — pages, components, API client (`src/api/mcsa.ts`), types (e.g. `src/types/mcsa.ts`)
  - `README.md` (existing UI README)
  - `Dockerfile`, `.dockerignore`

- `tayfin-app/tayfin-bff/` (BFF service)
  - `Dockerfile`, `requirements.txt`, `requirements-dev.txt`
  - `config/bff.yml` — BFF config
  - `scripts/run_bff.sh` — run helper
  - `src/tayfin_bff/app.py` — application entry and route registration
  - `src/tayfin_bff/clients/` — HTTP clients to other contexts (e.g. `clients/screener_client.py`)
  - `src/tayfin_bff/cli/main.py`, `__main__.py` — CLI entrypoints
  - `tests/` — unit tests and fixtures

Notes / next pointers
---------------------
- Use `tayfin-app/tayfin-bff/src/tayfin_bff/app.py` and `clients/` to extract authoritative request/response shapes for the BFF README.
- The UI's `src/api` directory contains client-side contracts (e.g. `mcsa.ts`) that inform expected payload shapes and endpoints.
- Config files (`config/bff.yml`) and `scripts/run_bff.sh` are useful for providing runnable examples in READMEs.
