#!/usr/bin/env bash
set -euo pipefail

# run_fundamentals.sh
# Helper to run the fundamentals job from the repository without thinking about
# PYTHONPATH or paths. Place this at tayfin-ingestor/tayfin-ingestor-jobs/scripts/

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

env_file="$repo_root/.env"
config_file="$repo_root/tayfin-ingestor/tayfin-ingestor-jobs/config/fundamentals.yml"
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
  echo "Listing fundamentals targets"
  python -m tayfin_ingestor_jobs jobs list --kind fundamentals --config "$config_file"
  exit 0
fi

echo "Running fundamentals job (nasdaq-100)"
python -m tayfin_ingestor_jobs jobs run fundamentals nasdaq-100 --config "$config_file"
