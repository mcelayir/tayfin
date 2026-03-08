Purpose: Backend-for-Frontend to serve the HTMX dashboard UI (ADR-0001 §D3).
Phase: Phase 1 — MCSA Trend Template dashboard.
Context: tayfin-app

## Stack

- **Flask** — app factory pattern (consistent with context APIs)
- **Jinja2** — server-rendered templates
- **HTMX** — dynamic partial updates (sorting, filtering, refresh)
- **httpx** — outbound calls to context APIs
- **Typer** — CLI entry point

## Usage

```bash
python -m tayfin_bff serve --port 8030 --debug
```

## Endpoints

| Path | Type | Description |
|------|------|-------------|
| `GET /` | Page | Redirect to MCSA dashboard |
| `GET /mcsa` | Page | MCSA Trend Template dashboard |
| `GET /htmx/mcsa/table` | Partial | Results table (HTMX fragment) |
| `GET /htmx/mcsa/histogram` | Partial | RS histogram (HTMX fragment) |
| `GET /api/mcsa/latest` | JSON | Proxy: latest MCSA results |
| `GET /api/mcsa/latest/<ticker>` | JSON | Proxy: single ticker |
| `GET /api/mcsa/range` | JSON | Proxy: date range |
| `GET /api/mcsa/rs-histogram` | JSON | RS rank distribution |
| `GET /health` | JSON | BFF + downstream health |

## Architecture

- UI calls **only** the BFF (§2.2)
- BFF proxies to screener API via `ScreenerClient`
- No direct DB access — read-only over context APIs
