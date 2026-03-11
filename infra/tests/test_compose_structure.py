"""
Structural validation of infra/docker-compose.yml against ADR-03.

Verifies:
  - All 7 services are declared (db, flyway, 4 APIs, ui).
  - Port allocations match ADR-03 § Port Allocation table.
  - Dependency chain matches ADR-03 § Service Dependency Chain.
  - DB-connected APIs receive POSTGRES_HOST=db override.
  - Inter-service URL env vars use Docker service names (ADR-05 §4).
  - UI receives VITE_API_TARGET pointing at BFF.
"""

from __future__ import annotations

import pathlib
import yaml
import pytest

COMPOSE_PATH = pathlib.Path(__file__).resolve().parents[1] / "docker-compose.yml"

# ── ADR-03 canonical values ──────────────────────────────────

EXPECTED_SERVICES = {"db", "flyway", "ingestor-api", "indicator-api",
                     "screener-api", "bff", "ui"}

PORT_MAP = {
    "ingestor-api": "8000:8000",
    "indicator-api": "8010:8010",
    "screener-api": "8020:8020",
    "bff": "8030:8030",
    "ui": "5173:5173",
    "db": "5432:5432",
}

# ADR-03 § Service Dependency Chain
DEPENDENCY_CHAIN: dict[str, dict[str, str]] = {
    "flyway":       {"db": "service_healthy"},
    "ingestor-api": {"flyway": "service_completed_successfully"},
    "indicator-api": {"flyway": "service_completed_successfully",
                      "ingestor-api": "service_healthy"},
    "screener-api": {"flyway": "service_completed_successfully"},
    "bff":          {"screener-api": "service_healthy"},
    "ui":           {"bff": "service_healthy"},
}

DB_CONNECTED = {"ingestor-api", "indicator-api", "screener-api"}


@pytest.fixture(scope="module")
def compose() -> dict:
    """Load and return the parsed compose file."""
    text = COMPOSE_PATH.read_text()
    return yaml.safe_load(text)


@pytest.fixture(scope="module")
def services(compose: dict) -> dict:
    return compose["services"]


# ── Tests ────────────────────────────────────────────────────

def test_all_services_declared(services: dict) -> None:
    """ADR-03: All 7 services must be present."""
    assert set(services.keys()) == EXPECTED_SERVICES


@pytest.mark.parametrize("svc,expected_port", PORT_MAP.items())
def test_port_allocation(services: dict, svc: str, expected_port: str) -> None:
    """ADR-03 § Port Allocation: host:container ports match."""
    ports = services[svc].get("ports", [])
    assert expected_port in ports, f"{svc} missing port mapping {expected_port}"


@pytest.mark.parametrize("svc,deps", DEPENDENCY_CHAIN.items())
def test_dependency_chain(services: dict, svc: str,
                          deps: dict[str, str]) -> None:
    """ADR-03 § Service Dependency Chain."""
    actual_deps = services[svc].get("depends_on", {})
    for dep_name, expected_condition in deps.items():
        assert dep_name in actual_deps, (
            f"{svc} must depend on {dep_name}")
        assert actual_deps[dep_name].get("condition") == expected_condition, (
            f"{svc} → {dep_name} condition must be {expected_condition}")


@pytest.mark.parametrize("svc", DB_CONNECTED)
def test_db_host_override(services: dict, svc: str) -> None:
    """ADR-05: DB-connected APIs must set POSTGRES_HOST=db."""
    env = services[svc].get("environment", {})
    assert env.get("POSTGRES_HOST") == "db", (
        f"{svc} must override POSTGRES_HOST to 'db'")


@pytest.mark.parametrize("svc", DB_CONNECTED)
def test_env_file_points_to_root(services: dict, svc: str) -> None:
    """ADR-05: DB-connected APIs load ../.env for POSTGRES_* vars."""
    env_file = services[svc].get("env_file")
    assert env_file == "../.env", f"{svc} must use env_file: ../.env"


def test_indicator_ingestor_url(services: dict) -> None:
    """ADR-05 §4: indicator-api points to ingestor-api by service name."""
    env = services["indicator-api"].get("environment", {})
    assert env.get("TAYFIN_INGESTOR_API_BASE_URL") == "http://ingestor-api:8000"


def test_bff_screener_url(services: dict) -> None:
    """ADR-05 §4: BFF points to screener-api by service name."""
    env = services["bff"].get("environment", {})
    assert env.get("TAYFIN_SCREENER_API_BASE_URL") == "http://screener-api:8020"


def test_ui_vite_target(services: dict) -> None:
    """ADR-03 § Vite Config: UI gets VITE_API_TARGET targeting BFF."""
    env = services["ui"].get("environment", {})
    assert env.get("VITE_API_TARGET") == "http://bff:8030"


def test_bff_has_no_db_env(services: dict) -> None:
    """BFF has no direct DB access — must NOT carry env_file or POSTGRES_HOST."""
    bff = services["bff"]
    assert "env_file" not in bff, "BFF should not load DB env vars"
    env = bff.get("environment", {})
    assert "POSTGRES_HOST" not in env, "BFF should not set POSTGRES_HOST"
