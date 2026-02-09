import httpx
import pytest
from tayfin_ingestor_jobs.db.engine import get_engine
from tayfin_ingestor_jobs.jobs.discovery_job import DiscoveryJob
from sqlalchemy import text


def test_discovery_network_failure(monkeypatch):
    """Simulate a network error during provider fetch and ensure the job is audited as FAILED."""
    # Monkeypatch httpx.Client.get to raise a connection error
    def fake_get(self, url, *args, **kwargs):
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    # Run the job and expect an exception
    job = DiscoveryJob.from_config(target_cfg={"code": "nasdaq100", "country": "US", "index_code": "NDX"})
    engine = get_engine()

    # Capture created job_run id before running by hacking repository create
    with pytest.raises(Exception):
        job.run()

    # Validate the most recent job_run entry is FAILED
    with engine.connect() as conn:
        row = conn.execute(text("SELECT status, error_summary FROM tayfin_ingestor.job_runs ORDER BY started_at DESC LIMIT 1")).fetchone()
        assert row is not None
        assert row[0] == "FAILED"
        assert "simulated network failure" in (row[1] or "")
