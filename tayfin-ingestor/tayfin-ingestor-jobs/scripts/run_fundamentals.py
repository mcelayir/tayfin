#!/usr/bin/env python3
"""Run the fundamentals job CLI from the repo root.

This script mirrors the project's run_discovery.sh helper but is a thin
python wrapper that loads .env and execs the CLI module.
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parents[3]
env_file = repo_root / ".env"
config_file = repo_root / "tayfin-ingestor" / "tayfin-ingestor-jobs" / "config" / "fundamentals.yml"
src_path = str(repo_root / "tayfin-ingestor" / "tayfin-ingestor-jobs" / "src")

if not env_file.exists():
    print(f"ERROR: .env not found at {env_file}")
    sys.exit(1)

load_dotenv(dotenv_path=env_file)

os.environ["PYTHONPATH"] = src_path

# Optional helper mode: pass 'list' as first arg to run the lightweight listing command
mode = sys.argv[1] if len(sys.argv) > 1 else "run"
if mode == "list":
    args = [sys.executable, "-m", "tayfin_ingestor_jobs", "jobs", "list", "--kind", "fundamentals", "--config", str(config_file)]
else:
    args = [sys.executable, "-m", "tayfin_ingestor_jobs", "jobs", "run", "fundamentals", "nasdaq-100", "--config", str(config_file)]

# Use subprocess.run with explicit env to ensure PYTHONPATH is used.
env = os.environ.copy()
env["PYTHONPATH"] = src_path
try:
    subprocess.run(args, check=True, env=env)
except subprocess.CalledProcessError as exc:
    sys.exit(exc.returncode)
