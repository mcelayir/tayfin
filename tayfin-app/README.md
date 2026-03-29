# tayfin-app

Purpose
-------
`tayfin-app` contains the user-facing applications for Tayfin: the Browser UI (`tayfin-ui`) and the Backend-For-Frontend service (`tayfin-bff`). This README summarizes responsibilities, local development, and integration points.

Scope
-----
- `tayfin-ui` — React + Vite single-page app under `tayfin-app/tayfin-ui`.
- `tayfin-bff` — BFF service that aggregates and proxies data for the UI under `tayfin-app/tayfin-bff`.

Quick Start
-----------
1. Read the `tayfin-bff` and `tayfin-ui` READMEs for component-level run instructions.
2. Start the BFF before the UI so the dev proxy and API calls resolve locally.

Components
----------
- UI: [tayfin-app/tayfin-ui/README.md](tayfin-app/tayfin-ui/README.md)
- BFF: [tayfin-app/tayfin-bff/README.md](tayfin-app/tayfin-bff/README.md)

Dev workflow (example)
----------------------
Run the BFF locally (from repo root):

```bash
cd tayfin-app/tayfin-bff
./scripts/run_bff.sh
```

Run the UI (from repo root):

```bash
cd tayfin-app/tayfin-ui
npm install
npm run dev
```

Environment & Configuration
---------------------------
Key env vars used by App components (examples):

- `TAYFIN_BFF_BASE_URL` — Base URL for the BFF. Example: `http://localhost:8030`
- `NODE_ENV` — `development` / `production` used by the UI build tooling.

Links
-----
- Artifacts inventory: [tayfin-app/artifacts.md](tayfin-app/artifacts.md)
- BFF README: [tayfin-app/tayfin-bff/README.md](tayfin-app/tayfin-bff/README.md)
- UI README: [tayfin-app/tayfin-ui/README.md](tayfin-app/tayfin-ui/README.md)

Next steps
----------
1. Verify BFF endpoints and UI proxy settings in local dev.
2. Add validation metadata headers to these READMEs (E36-06.6).