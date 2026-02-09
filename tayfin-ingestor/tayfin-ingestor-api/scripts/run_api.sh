#!/usr/bin/env bash
set -euo pipefail

# Installs requirements and runs the Flask API for local development
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$ROOT_DIR/requirements.txt"

if [ -f "$REQ" ]; then
  echo "Installing requirements from $REQ"
  python -m pip install --upgrade pip
  python -m pip install -r "$REQ"
else
  echo "requirements.txt not found at $REQ" >&2
fi

export PYTHONPATH="$ROOT_DIR/src"
echo "Starting API (PYTHONPATH=$PYTHONPATH)"
exec flask --app tayfin_ingestor_api.app run --host 0.0.0.0 --port 8000
