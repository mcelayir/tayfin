"""
End-to-end smoke tests for the full Docker Compose stack.

These tests hit the **live** services via localhost ports.
They require a running ``docker compose up -d`` stack.

Run with::

    pytest infra/tests/test_e2e_smoke.py -v

What is verified
~~~~~~~~~~~~~~~~
1. All API /health endpoints return 200 + {"status": "ok"}.
2. UI returns 200 with HTML containing expected Vite markers.
3. DB-connected APIs can query their schemas (SELECT 1 via /health DB check).
4. Inter-service communication works (BFF → screener-api via /api/mcsa/dashboard).
5. indicator-api → ingestor-api connectivity (upstream env var resolves).
6. Container env vars are correctly injected (POSTGRES_HOST=db, inter-service URLs).
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
import urllib.error

import pytest

# ── Helpers ──────────────────────────────────────────────────

_TIMEOUT = 5  # seconds


def _get(url: str, *, timeout: int = _TIMEOUT) -> tuple[int, str]:
    """GET a URL and return (status_code, body_text)."""
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def _get_json(url: str) -> tuple[int, dict]:
    """GET and parse JSON."""
    code, body = _get(url)
    return code, json.loads(body)


def _docker_exec_env(container: str, var: str) -> str:
    """Read an env var from inside a running container."""
    result = subprocess.run(
        ["docker", "exec", container, "printenv", var],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


# ── Fixtures ─────────────────────────────────────────────────

COMPOSE_CONTAINERS = {
    "ingestor-api": "infra-ingestor-api-1",
    "indicator-api": "infra-indicator-api-1",
    "screener-api": "infra-screener-api-1",
    "bff": "infra-bff-1",
    "ui": "infra-ui-1",
}


# ── 1. Health Endpoints ─────────────────────────────────────

@pytest.mark.parametrize("svc,port", [
    ("ingestor-api", 8000),
    ("indicator-api", 8010),
    ("screener-api", 8020),
    ("bff", 8030),
])
def test_api_health_200(svc: str, port: int) -> None:
    """Every Python API /health returns 200 + {"status": "ok"}."""
    code, data = _get_json(f"http://localhost:{port}/health")
    assert code == 200, f"{svc} health returned {code}"
    assert data["status"] == "ok", f"{svc} health status: {data}"


def test_ui_returns_html() -> None:
    """UI on :5173 returns 200 with HTML content."""
    code, body = _get("http://localhost:5173")
    assert code == 200, f"UI returned {code}"
    assert "<html" in body.lower() or "<!doctype" in body.lower(), (
        "UI did not return HTML")


# ── 2. DB Connectivity (via health checks with DB pings) ────

@pytest.mark.parametrize("svc,port", [
    ("screener-api", 8020),
    ("indicator-api", 8010),
])
def test_db_health_check(svc: str, port: int) -> None:
    """Services with DB ping in /health confirm DB connectivity."""
    code, data = _get_json(f"http://localhost:{port}/health")
    assert code == 200, f"{svc} DB health failed: {data}"
    assert data["status"] == "ok"


# ── 3. Inter-Service Communication ──────────────────────────

def test_bff_to_screener_api() -> None:
    """BFF /api/mcsa/dashboard proxies through to screener-api.

    Expects either 200 (if data exists) or 200 with empty results —
    NOT a 502/503/connection-refused, which would indicate broken routing.
    """
    code, body = _get(f"http://localhost:8030/api/mcsa/dashboard", timeout=30)
    # Any 2xx or a structured 4xx error is fine — it means BFF reached screener
    assert code < 500, (
        f"BFF→screener proxy returned {code}, indicates broken inter-service "
        f"comm: {body[:200]}")


def test_indicator_api_ingestor_env() -> None:
    """indicator-api container has TAYFIN_INGESTOR_API_BASE_URL set to
    the Docker service name (not localhost)."""
    val = _docker_exec_env(
        COMPOSE_CONTAINERS["indicator-api"],
        "TAYFIN_INGESTOR_API_BASE_URL",
    )
    assert val == "http://ingestor-api:8000", f"Got: {val!r}"


def test_bff_screener_env() -> None:
    """BFF container has TAYFIN_SCREENER_API_BASE_URL set to
    the Docker service name."""
    val = _docker_exec_env(
        COMPOSE_CONTAINERS["bff"],
        "TAYFIN_SCREENER_API_BASE_URL",
    )
    assert val == "http://screener-api:8020", f"Got: {val!r}"


def test_ui_vite_target_env() -> None:
    """UI container has VITE_API_TARGET pointing at BFF."""
    val = _docker_exec_env(
        COMPOSE_CONTAINERS["ui"],
        "VITE_API_TARGET",
    )
    assert val == "http://bff:8030", f"Got: {val!r}"


# ── 4. Container Env: POSTGRES_HOST=db ──────────────────────

@pytest.mark.parametrize("svc", ["ingestor-api", "indicator-api", "screener-api"])
def test_postgres_host_is_db(svc: str) -> None:
    """DB-connected APIs have POSTGRES_HOST=db inside the container."""
    val = _docker_exec_env(COMPOSE_CONTAINERS[svc], "POSTGRES_HOST")
    assert val == "db", f"{svc} POSTGRES_HOST={val!r}, expected 'db'"


# ── 5. DB Query from Containers ─────────────────────────────

@pytest.mark.parametrize("container,package", [
    ("infra-ingestor-api-1", "tayfin_ingestor_api"),
    ("infra-indicator-api-1", "tayfin_indicator_api"),
    ("infra-screener-api-1", "tayfin_screener_api"),
])
def test_db_select_from_container(container: str, package: str) -> None:
    """Each DB container can run SELECT 1 through its engine."""
    script = (
        f"import sqlalchemy as sa\n"
        f"from {package}.db.engine import get_engine\n"
        f"e = get_engine()\n"
        f"with e.connect() as c:\n"
        f"    r = c.execute(sa.text('SELECT 1'))\n"
        f"    print(r.scalar())\n"
    )
    result = subprocess.run(
        ["docker", "exec", container, "python", "-c", script],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, (
        f"{container} DB query failed: {result.stderr}")
    assert result.stdout.strip() == "1"
