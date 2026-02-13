# tayfin-indicator

Bounded context for **technical-indicator computation and storage**.

## Sub-applications

| App | Purpose |
|-----|---------|
| `tayfin-indicator-jobs` | CLI / scheduled jobs that compute indicators |
| `tayfin-indicator-api`  | Read-only REST API exposing computed indicators |

## Database

Flyway-managed migrations live in `db/migrations/`.
Schema: `indicator` (created by the init migration).
