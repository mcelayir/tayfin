#!/usr/bin/env python3
"""
Minimal scheduler prototype for Compose dev.
Reads infra/schedules.yml and can run in --once mode to execute all scheduled jobs immediately.
"""
import argparse
import shlex
import subprocess
import sys
import os
import time
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
    # Reuse a single DB connection for advisory lock operations during this run.
    # Try to connect with a small retry loop so scheduler waits briefly for DB readiness.
    conn = None
    max_attempts = int(os.environ.get("SCHEDULER_DB_CONNECT_ATTEMPTS", "6"))
    wait_seconds = int(os.environ.get("SCHEDULER_DB_CONNECT_WAIT", "5"))
    for attempt in range(1, max_attempts + 1):
        try:
            conn = db_lock.get_connection()
            break
        except Exception as e:
            print(f"[scheduler] warning: DB connect attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                time.sleep(wait_seconds)
    if conn is None:
        print("[scheduler] warning: proceeding without shared DB connection; advisory locks will be skipped")

    try:
        # Group schedules by module (derived from `python -m <module>` in the cmd)
        module_groups: dict[str, list[tuple[str, str]]] = {}
        for name, cfg in schedules.items():
            cmd = cfg.get("cmd")
            if not cmd:
                print(f"[scheduler] schedule {name} has no cmd, skipping")
                continue
            # extract module after `-m`
            parts = cmd.split()
            module = None
            if "-m" in parts:
                try:
                    m_idx = parts.index("-m")
                    module = parts[m_idx + 1]
                except Exception:
                    module = None
            # fallback: try pattern `python -m modulename`
            if module is None:
                # crude fallback: take second token when command starts with python
                if parts and parts[0].endswith("python") and len(parts) > 2 and parts[1] == "-m":
                    module = parts[2]

            mod_key = module or "unknown"
            module_groups.setdefault(mod_key, []).append((name, cmd))

        # Desired execution order of modules
        preferred_order = ["tayfin_ingestor_jobs", "tayfin_indicator_jobs", "tayfin_screener_jobs"]

        # Build ordered list of modules to execute: preferred order first, then the rest
        ordered_modules: list[str] = []
        for p in preferred_order:
            if p in module_groups:
                ordered_modules.append(p)
        # append any remaining module keys (preserve insertion order)
        for k in module_groups.keys():
            if k not in ordered_modules:
                ordered_modules.append(k)

        # Execute groups in order
        for mod in ordered_modules:
            entries = module_groups.get(mod, [])
            # If this is the ingestor module, prefer to run discovery jobs first.
            if mod == "tayfin_ingestor_jobs" and entries:
                # discovery commands look like: '... jobs run discovery <target> ...'
                discovery = [e for e in entries if "jobs run discovery" in e[1]]
                others = [e for e in entries if "jobs run discovery" not in e[1]]
                entries = discovery + others

            print(f"[scheduler] executing module group: {mod} ({len(entries)} jobs)")
            # Execute jobs sequentially within the module group
            for name, cmd in entries:
                # Try to acquire advisory lock only if we have a shared connection.
                acquired = True
                if conn is not None:
                    try:
                        acquired = db_lock.try_acquire_lock(name, conn=conn)
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
                    if conn is not None:
                        try:
                            db_lock.release_lock(name, conn=conn)
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
