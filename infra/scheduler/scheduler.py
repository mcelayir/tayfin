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
import db_lock

# Prefer schedules file copied into image at /app/schedules.yml (when running in
# the scheduler container). Fall back to repo-relative path when running from
# source checkout.
ROOT = Path(__file__).resolve().parent
SCHEDULES_FILE = ROOT / "schedules.yml"
if not SCHEDULES_FILE.exists():
    try:
        ROOT = Path(__file__).resolve().parents[2]
        SCHEDULES_FILE = ROOT / "infra" / "schedules.yml"
    except IndexError:
        SCHEDULES_FILE = ROOT / "schedules.yml"


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
    # Reuse a single DB connection for advisory lock operations during this run
    conn = None
    try:
        try:
            conn = db_lock.get_connection()
        except Exception:
            conn = None

        for name, cfg in schedules.items():
            cmd = cfg.get("cmd")
            if not cmd:
                print(f"[scheduler] schedule {name} has no cmd, skipping")
                continue
            # Acquire advisory lock to prevent overlapping runs.
            acquired = False
            try:
                if conn is not None:
                    acquired = db_lock.try_acquire_lock(name, conn=conn)
                else:
                    acquired = db_lock.try_acquire_lock(name)
            except Exception as e:
                print(f"[scheduler] warning: could not acquire lock for {name}: {e}")
                # proceed to attempt run if locking fails
                acquired = True

            if not acquired:
                print(f"[scheduler] lock not acquired for {name}, skipping")
                continue

            try:
                ok = run_command(cmd)
                if not ok:
                    failures.append(name)
            finally:
                try:
                    if conn is not None:
                        db_lock.release_lock(name, conn=conn)
                    else:
                        db_lock.release_lock(name)
                except Exception as e:
                    print(f"[scheduler] warning: failed to release lock for {name}: {e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

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
