"""
Validate infra/README.md documents all services, ports, and env vars.

Light-touch content checks — verifies the README stays in sync with
docker-compose.yml and .env.example as the stack evolves.
"""

from __future__ import annotations

import pathlib
import re

import pytest

INFRA = pathlib.Path(__file__).resolve().parents[1]
README = INFRA / "README.md"

# These must appear in the README to keep docs accurate.
REQUIRED_SERVICES = [
    "ingestor-api", "indicator-api", "screener-api", "bff", "ui",
    "db", "flyway",
]

REQUIRED_PORTS = ["5432", "8000", "8010", "8020", "8030", "5173"]

REQUIRED_ENV_VARS = [
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
    "POSTGRES_USER", "POSTGRES_PASSWORD",
    "TAYFIN_INGESTOR_API_BASE_URL",
    "TAYFIN_INDICATOR_API_BASE_URL",
    "TAYFIN_SCREENER_API_BASE_URL",
    "VITE_API_TARGET",
]

REQUIRED_SECTIONS = [
    "Quick Start", "Service Inventory", "Environment Variables",
    "Common Operations", "Health Checks", "Troubleshooting",
]


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text()


def test_readme_exists() -> None:
    assert README.exists(), "infra/README.md must exist"


@pytest.mark.parametrize("svc", REQUIRED_SERVICES)
def test_service_documented(readme_text: str, svc: str) -> None:
    assert svc in readme_text, f"Service '{svc}' not documented in README"


@pytest.mark.parametrize("port", REQUIRED_PORTS)
def test_port_documented(readme_text: str, port: str) -> None:
    assert port in readme_text, f"Port {port} not documented in README"


@pytest.mark.parametrize("var", REQUIRED_ENV_VARS)
def test_env_var_documented(readme_text: str, var: str) -> None:
    assert var in readme_text, f"Env var {var} not documented in README"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_section_present(readme_text: str, section: str) -> None:
    assert section in readme_text, f"Section '{section}' missing from README"
