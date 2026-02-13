#!/usr/bin/env bash
set -euo pipefail

# Installs requirements and runs the Flask API for local development
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$ROOT_DIR/requirements.txt"

# load repo root .env if present (two levels above API folder)
REPO_ROOT="$(cd "$ROOT_DIR/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment from $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

if [ -f "$REQ" ]; then
  echo "Installing requirements from $REQ"
  python -m pip install --upgrade pip -q
  python -m pip install -r "$REQ" -q
else
  echo "requirements.txt not found at $REQ" >&2
fi

export PYTHONPATH="$ROOT_DIR/src"
echo "Starting tayfin-indicator-api (PYTHONPATH=$PYTHONPATH)"
exec flask --app tayfin_indicator_api.app run --host 0.0.0.0 --port 8010
