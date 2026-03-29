# tayfin-ui

**Purpose:** React + TypeScript UI for the Tayfin MCSA Score Dashboard.  
**Context:** `tayfin-app`  
**Framework:** React 19 + TypeScript 5.8 + Vite 6 (per ADR-02)

## Architecture

- UI calls **only** the BFF at `/api/*` — never context APIs directly (§2.2)
- Dev: Vite `:5173` proxies `/api` to BFF `:8030`
- Prod: Flask BFF serves built `dist/` as static files

## Development

```bash
# Install deps
npm install

# Start dev server (with HMR)
npm run dev

# Build for production
npm run build
```

## Project Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Router + layout
├── api/
│   └── mcsa.ts           # Typed BFF API client
├── components/
│   ├── ScoreTable/       # Primary data table
│   ├── DetailPanel/      # Expanded row detail view
│   ├── FilterBar/        # Band/score/search filters
│   ├── SummaryBar/       # Distribution visualization
│   └── common/           # BandBadge, ProgressBar
├── hooks/
│   └── useMcsaData.ts    # Data fetching hook
├── types/
│   └── mcsa.ts           # TypeScript interfaces
├── theme/
│   └── tokens.css        # CSS custom properties
└── pages/
    └── Dashboard.tsx      # Main dashboard page
```

## Environment Variables

Key environment variables used by the UI (examples):

- `TAYFIN_BFF_BASE_URL` — Base URL for the BFF used by the client. Example: `http://localhost:8030`
- `VITE_DEV_SERVER_PORT` — Vite dev server port. Example: `5173`
- `NODE_ENV` — Build mode (`development`/`production`). Example: `development`

Dev proxy note
-------------
The Vite dev server proxies `/api` requests to the BFF. Confirm `vite.config.ts` proxy settings when troubleshooting API calls.
