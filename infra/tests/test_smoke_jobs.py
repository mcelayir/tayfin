import subprocess
import sys

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
    cmd = [sys.executable, "-m", module, "jobs", "list"]
    res = subprocess.run(cmd, check=False)
    assert res.returncode == 0
