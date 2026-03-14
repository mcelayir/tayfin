#!/usr/bin/env python3
"""
Minimal scheduler prototype for Compose dev.
Reads infra/schedules.yml and can run in --once mode to execute all scheduled jobs immediately.
"""
import argparse
import shlex
import subprocess
import sys
from pathlib import Path
import yaml
from typing import Dict

ROOT = Path(__file__).resolve().parents[2]
SCHEDULES_FILE = ROOT / "infra" / "schedules.yml"


def load_schedules(path: Path):
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def run_command(cmd: str):
    print(f"[scheduler] executing: {cmd}")
    # Use shlex.split to avoid shell=True and reduce shell-injection risk.
    try:
        args = shlex.split(cmd)
        proc = subprocess.run(args, check=True, capture_output=True, text=True)
        print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[scheduler] command failed (rc={e.returncode}): {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False
    return True


def run_once(schedules: dict):
    failures = []
    for name, cfg in schedules.items():
        cmd = cfg.get("cmd")
        if not cmd:
            print(f"[scheduler] schedule {name} has no cmd, skipping")
            continue
        # Example: integrate DB advisory locks here to prevent overlapping runs.
        # from infra.scheduler.db_lock import make_lock_key
        # lock_key = make_lock_key(name)
        # TODO: acquire advisory lock using a DB connection before running.
        ok = run_command(cmd)
        if not ok:
            failures.append(name)
    if failures:
        print(f"[scheduler] failures: {failures}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run all schedules once and exit")
    args = parser.parse_args()

    schedules = load_schedules(SCHEDULES_FILE)
    if not schedules:
        print("[scheduler] no schedules found")
        return

    if args.once:
        run_once(schedules)
    else:
        print("[scheduler] currently only --once is implemented for the prototype")


if __name__ == "__main__":
    main()
