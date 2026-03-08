#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Helper: run screener jobs from repo root
# Usage:
#   ./scripts/run_screener.sh list
#   ./scripts/run_screener.sh run vcp_screen nasdaq-100 --config config/screener.yml
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONTEXT_ROOT="$REPO_ROOT/tayfin-screener/tayfin-screener-jobs"

# Load .env if present
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; source "$REPO_ROOT/.env"; set +a
fi

# Activate or create venv
VENV_DIR="$CONTEXT_ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$CONTEXT_ROOT/requirements.txt"
fi
source "$VENV_DIR/bin/activate"
export PYTHONPATH="$CONTEXT_ROOT/src:${PYTHONPATH:-}"

if [[ "${1:-}" == "list" ]]; then
  python -m tayfin_screener_jobs jobs list "${@:2}"
else
  python -m tayfin_screener_jobs jobs "$@"
fi
