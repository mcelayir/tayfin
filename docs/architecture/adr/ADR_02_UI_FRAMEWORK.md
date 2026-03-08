# Architecture Decision Record: UI Framework

## Status

**Accepted**

## Context

The Tayfin platform requires a user interface to display MCSA (Minervini Chartist Scoring Algorithm) scores for NASDAQ-100 stocks. The UI lives within the `tayfin-app` bounded context alongside the BFF (Backend-for-Frontend).

Current state:

- `tayfin-app/tayfin-bff/` — empty skeleton (README only). Will use Flask + Typer per TECH_STACK_RULES §3, §6.
- `tayfin-app/tayfin-ui/` — empty skeleton (README only). Framework not yet decided.
- Screener API — fully operational with 3 MCSA endpoints returning scores, bands, component breakdowns, and evidence JSON.

The UI must support:

- Sortable data table with 100+ rows (one per NDX ticker)
- Client-side filtering (band, min score, ticker search)
- Click-to-expand detail panel with component breakdown and evidence visualization
- Mini progress bars and donut charts for score components
- URL query param sync for filter state
- Dark theme with trading-grade data density

This document decides the frontend framework for `tayfin-ui`.

---

## Options Considered

### Option A — HTMX + Flask / Jinja2 (Server-Rendered)

**Description:** Server-rendered HTML with HTMX for partial page updates. No JavaScript build chain. Templates live in the BFF alongside Flask routes.

**Pros:**

- Zero build tooling — no Node.js, no bundler, no transpiler
- Aligns with "local-first simplicity" philosophy
- Single deployment unit (BFF serves both API and HTML)
- Minimal client-side JavaScript
- Was previously used in the Issue #11 (MCSA Trend Template) prototype

**Cons:**

- Limited interactivity for complex UI patterns (sortable tables, expandable rows, charts)
- HTMX partial swaps become unwieldy with multiple interactive controls on one page
- No component model — templating is flat, hard to test in isolation
- Chart rendering requires inline `<script>` or additional JS libraries anyway
- Poor developer experience for complex UIs: no type checking, no component reuse, no IDE support for template logic
- State management across filters, sort, and expanded rows requires manual DOM manipulation

**Verdict:** Suitable for simple CRUD dashboards but insufficient for the data density and interactivity required by the MCSA score dashboard.

---

### Option B — React + TypeScript + Vite

**Description:** Single-page application built with React and TypeScript, bundled with Vite. Served as static assets by the BFF or a simple static file server.

**Pros:**

- Full component model — each UI element (table row, detail panel, filter bar, chart) is a testable, reusable component
- TypeScript provides compile-time type safety for API response shapes (MCSA score structure, evidence JSON)
- Vite provides fast HMR (hot module replacement) during development
- Rich ecosystem for data tables (TanStack Table), charts (Chart.js, Recharts), and accessibility
- Client-side sorting and filtering is trivial with React state (dataset ≤101 items)
- URL sync via react-router search params
- Component testing with React Testing Library
- Industry standard for financial dashboards

**Cons:**

- Introduces Node.js build chain (npm/pnpm, Vite, TypeScript compiler)
- Separate development server during dev (port 5173 for Vite, port 5000 for BFF)
- Adds ~50MB of `node_modules` to the workspace
- Requires CORS configuration on BFF during development (Vite proxy solves this)
- Slightly more complex deployment: BFF serves built static files from `dist/`

**Verdict:** Best fit for the required interactivity, data density, and developer experience.

---

## Decision

**React + TypeScript + Vite** is adopted as the UI framework for `tayfin-ui`.

---

## Implementation Guidelines

### Project Structure

```
tayfin-app/tayfin-ui/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
├── src/
│   ├── main.tsx              # React entry point
│   ├── App.tsx               # Router + layout
│   ├── api/                  # BFF API client
│   │   └── mcsa.ts           # typed fetch wrappers
│   ├── components/           # reusable UI components
│   │   ├── ScoreTable/
│   │   ├── DetailPanel/
│   │   ├── FilterBar/
│   │   ├── SummaryBar/
│   │   └── common/           # Badge, ProgressBar, etc.
│   ├── hooks/                # custom React hooks
│   ├── types/                # TypeScript interfaces
│   │   └── mcsa.ts           # McsaResult, Evidence, etc.
│   ├── theme/                # CSS variables, tokens
│   │   └── tokens.css
│   └── pages/
│       └── Dashboard.tsx
└── tests/
```

### Key Dependencies

| Package | Purpose | Version Policy |
|---|---|---|
| `react` + `react-dom` | UI library | Latest 18.x or 19.x |
| `typescript` | Type safety | Latest 5.x |
| `vite` | Build tool + dev server | Latest 6.x |
| `@vitejs/plugin-react` | React JSX transform | Match Vite |
| `react-router` | Client-side routing | Latest 7.x |

Optional (evaluated per task):

| Package | Purpose | When |
|---|---|---|
| `@tanstack/react-table` | Headless table with sorting | Task 6 (Score Table) |
| `chart.js` + `react-chartjs-2` | Donut chart in detail panel | Task 7 (Detail Panel) |
| `vitest` + `@testing-library/react` | Unit + component testing | Task 10 (Tests) |

### BFF Integration

- **Development:** Vite dev server on `:5173` with proxy to BFF on `:5000` (configured in `vite.config.ts`)
- **Production:** BFF serves the built `dist/` folder as static files at `/` and API routes at `/api/*`
- UI calls only `/api/*` endpoints on the BFF — never calls context APIs directly (ARCHITECTURE_RULES §2.2)

### Development Workflow

```bash
# Terminal 1 — BFF
cd tayfin-app/tayfin-bff
python -m tayfin_bff serve

# Terminal 2 — UI
cd tayfin-app/tayfin-ui
npm run dev
```

Vite proxy config:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000'
    }
  }
})
```

### Production Build

```bash
cd tayfin-app/tayfin-ui
npm run build    # outputs to dist/
```

BFF serves `dist/` as static files. No separate Node.js server in production.

### TypeScript Types for MCSA

The UI must define TypeScript interfaces matching the BFF/Screener API response:

```typescript
interface McsaResult {
  ticker: string;
  instrument_id: string | null;
  as_of_date: string;           // ISO date
  mcsa_score: number;           // 0–100
  mcsa_band: 'strong' | 'watchlist' | 'neutral' | 'weak';
  trend_score: number;          // 0–30
  vcp_component: number;        // 0–35
  volume_score: number;         // 0–15
  fundamental_score: number;    // 0–20
  evidence: McsaEvidence;
  missing_fields: string[];
}

interface McsaEvidence {
  trend: TrendEvidence;
  vcp: VcpEvidence;
  volume: VolumeEvidence;
  fundamentals: FundamentalsEvidence;
  total_score: number;
  band: string;
}
```

---

## Constraints

- `tayfin-ui` MUST NOT import from any other bounded context's code
- `tayfin-ui` MUST NOT call Screener API, Indicator API, or Ingestor API directly
- `tayfin-ui` MUST only communicate with the BFF at `/api/*`
- `node_modules/` MUST be in `.gitignore`
- The UI MUST work as static files served by Flask in production — no SSR, no Node.js runtime in production

---

## Consequences

**Benefits:**

- Component-based architecture enables isolated testing and reuse
- TypeScript catches API shape mismatches at compile time
- Vite provides sub-second HMR for rapid development
- Rich library ecosystem for tables, charts, and accessibility
- Industry-standard tooling familiar to most frontend developers

**Trade-offs:**

- Introduces Node.js as a development dependency (not production)
- `node_modules/` adds disk footprint (~50MB)
- Requires learning React patterns for developers unfamiliar with the framework
- CORS/proxy setup needed during development (one-time Vite config)

**Mitigations:**

- Vite proxy eliminates CORS issues during dev
- Production deployment remains Python-only (Flask serves static files)
- `.gitignore` keeps node_modules out of version control
- TypeScript interfaces derived directly from API response schemas — single source of truth

---

## References

- ARCHITECTURE_RULES §2.2 — UI MUST call only the BFF
- TECH_STACK_RULES §6 — Flask APIs (BFF)
- ADR-01 — MCSA Score Calculation Algorithm (defines evidence schema)
- Epic #20 — MCSA Score Dashboard
- `docs/ui/DESIGN_SPEC_MCSA_DASHBOARD.md` — wireframes and interaction model
- `docs/ui/THEME.md` — CSS token definitions
