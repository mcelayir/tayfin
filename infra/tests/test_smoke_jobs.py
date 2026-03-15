import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.smoke
@pytest.mark.parametrize(
    "module",
    [
        "tayfin_ingestor_jobs.cli.main",
        "tayfin_indicator_jobs.cli.main",
        "tayfin_screener_jobs.cli.main",
    ],
)
def test_job_cli_list(module):
    """Ensure each job package CLI can be imported and list jobs (exit code 0)."""
    repo_root = Path(__file__).resolve().parents[2]
    # Add job package src dirs to PYTHONPATH so `-m` imports work in CI and local runs
    src_paths = [
        str(repo_root / "tayfin-ingestor" / "tayfin-ingestor-jobs" / "src"),
        str(repo_root / "tayfin-indicator" / "tayfin-indicator-jobs" / "src"),
        str(repo_root / "tayfin-screener" / "tayfin-screener-jobs" / "src"),
    ]
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([*(existing.split(os.pathsep) if existing else []), *src_paths])

    cmd = [sys.executable, "-m", module, "jobs", "list"]
    res = subprocess.run(cmd, check=False, env=env)
    assert res.returncode == 0, f"module {module} failed with exit {res.returncode}"
