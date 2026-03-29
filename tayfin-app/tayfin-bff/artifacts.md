<!--
Artifacts inventory for `tayfin-bff` (E36-06.1)
Generated: 2026-03-29
Owner: @dev
-->
# tayfin-bff artifacts

Authoritative files and locations for the BFF component:

- `tayfin-app/tayfin-bff/Dockerfile`
- `tayfin-app/tayfin-bff/requirements.txt`
- `tayfin-app/tayfin-bff/requirements-dev.txt`
- `tayfin-app/tayfin-bff/config/bff.yml` — service configuration
- `tayfin-app/tayfin-bff/scripts/run_bff.sh` — run helper
- `tayfin-app/tayfin-bff/src/tayfin_bff/app.py` — FastAPI/Flask app entry (route handlers)
- `tayfin-app/tayfin-bff/src/tayfin_bff/clients/` — clients used by BFF (screener, indicator clients)
  - `clients/screener_client.py`
- `tayfin-app/tayfin-bff/src/tayfin_bff/cli/main.py` — CLI hooks
- `tayfin-app/tayfin-bff/tests/` — unit tests for config, health, and clients

Suggested extraction targets for README work:
- Use `app.py` to enumerate endpoints and example responses.
- Inspect `clients/` to document how the BFF calls upstream services (auth, timeouts, base URLs).
- Use `config/bff.yml` for example config and `scripts/run_bff.sh` for run commands in README examples.
