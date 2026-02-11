#!/usr/bin/env bash
set -euo pipefail

# run_ohlcv.sh
# Helper to run the OHLCV ingestion job.
# Usage:
#   ./run_ohlcv.sh                         # full NDX run
#   ./run_ohlcv.sh list                    # list OHLCV targets
#   ./run_ohlcv.sh --ticker AAPL           # single ticker debug
#   ./run_ohlcv.sh --from 2025-01-01       # custom date window
#   ./run_ohlcv.sh --ticker MSFT --from 2025-06-01 --to 2025-12-31
#   ./run_ohlcv.sh --limit 5               # first 5 tickers only (testing)

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

env_file="$repo_root/.env"
config_file="$repo_root/tayfin-ingestor/tayfin-ingestor-jobs/config/ohlcv.yml"
src_path="$repo_root/tayfin-ingestor/tayfin-ingestor-jobs/src"
requirements_file="$repo_root/tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt"
venv_dir="$repo_root/tayfin-ingestor/tayfin-ingestor-jobs/.venv"

if [ ! -f "$env_file" ]; then
  echo "ERROR: .env not found at $env_file"
  exit 1
fi

if [ ! -f "$config_file" ]; then
  echo "ERROR: config not found at $config_file"
  exit 1
fi

echo "Sourcing $env_file"
# shellcheck disable=SC1090
source "$env_file"

if [ -f "$requirements_file" ]; then
  if [ ! -d "$venv_dir" ]; then
    echo "Creating venv at $venv_dir"
    python -m venv "$venv_dir"
    echo "Upgrading pip and installing requirements into venv"
    "$venv_dir/bin/python" -m pip install --upgrade pip
    "$venv_dir/bin/python" -m pip install -r "$requirements_file"
  else
    echo "Using existing venv at $venv_dir"
  fi
  # Activate the venv for the run
  # shellcheck disable=SC1091
  source "$venv_dir/bin/activate"
else
  echo "WARNING: requirements file not found at $requirements_file — skipping venv setup"
fi

export PYTHONPATH="$src_path"

if [ "${NO_RUN:-0}" = "1" ]; then
  echo "NO_RUN=1 — venv prepared, skipping execution"
  exit 0
fi

# Allow optional 'list' mode
if [ "${1:-}" = "list" ]; then
  echo "Listing OHLCV targets"
  python -m tayfin_ingestor_jobs jobs list --kind ohlcv --config "$config_file"
  exit 0
fi

# Pass through all CLI args (--ticker, --from, --to)
echo "Running OHLCV job (nasdaq-100)"
python -m tayfin_ingestor_jobs jobs run ohlcv nasdaq-100 --config "$config_file" "$@"
