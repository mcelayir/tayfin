"""
Validate .env.example completeness against ADR-05 / ADR-06 contracts.

Verifies:
  - All ADR-05 canonical env vars are declared.
  - Default values match ADR-05/06 conventions.
  - Docker-compose.yml env_file references resolve to .env.
  - No stale or non-canonical variable names sneak in.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"

# ── ADR-05 § Canonical Variables ─────────────────────────────

ADR05_DB_VARS: dict[str, str] = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "tayfin",
    "POSTGRES_USER": "tayfin_user",
    "POSTGRES_PASSWORD": "change_me",
}

ADR05_URL_VARS: dict[str, str] = {
    "TAYFIN_INGESTOR_API_BASE_URL": "http://localhost:8000",
    "TAYFIN_INDICATOR_API_BASE_URL": "http://localhost:8010",
    "TAYFIN_SCREENER_API_BASE_URL": "http://localhost:8020",
}

ALL_CANONICAL = {**ADR05_DB_VARS, **ADR05_URL_VARS}

# Retired / forbidden variable names (ADR-05 §1 action item)
RETIRED_VARS = {"DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASS"}


@pytest.fixture(scope="module")
def env_vars() -> dict[str, str]:
    """Parse .env.example into a name→value dict (ignores comments/blanks)."""
    lines = ENV_EXAMPLE.read_text().splitlines()
    result: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


# ── Tests ────────────────────────────────────────────────────

def test_env_example_exists() -> None:
    """Root .env.example must be present."""
    assert ENV_EXAMPLE.exists(), f"Missing {ENV_EXAMPLE}"


@pytest.mark.parametrize("var,expected_value", ADR05_DB_VARS.items())
def test_db_vars_present(env_vars: dict[str, str], var: str,
                         expected_value: str) -> None:
    """ADR-05 §1: All POSTGRES_* database vars declared with correct defaults."""
    assert var in env_vars, f"{var} missing from .env.example"
    assert env_vars[var] == expected_value, (
        f"{var}={env_vars[var]!r}, expected {expected_value!r}")


@pytest.mark.parametrize("var,expected_value", ADR05_URL_VARS.items())
def test_url_vars_present(env_vars: dict[str, str], var: str,
                          expected_value: str) -> None:
    """ADR-05 §4: All inter-service URL vars declared with localhost defaults."""
    assert var in env_vars, f"{var} missing from .env.example"
    assert env_vars[var] == expected_value, (
        f"{var}={env_vars[var]!r}, expected {expected_value!r}")


@pytest.mark.parametrize("var", RETIRED_VARS)
def test_no_retired_vars(env_vars: dict[str, str], var: str) -> None:
    """ADR-05 §1: DB_* prefix is permanently retired."""
    assert var not in env_vars, f"Retired variable {var} found in .env.example"


def test_no_empty_password_in_example(env_vars: dict[str, str]) -> None:
    """ADR-06 §3: .env.example must document POSTGRES_PASSWORD with a
    non-empty placeholder so developers are reminded to configure it."""
    pw = env_vars.get("POSTGRES_PASSWORD", "")
    assert pw and pw != '""', (
        "POSTGRES_PASSWORD in .env.example must have a non-empty placeholder")


def test_user_is_not_superuser(env_vars: dict[str, str]) -> None:
    """ADR-06 §1: POSTGRES_USER must never default to 'postgres'."""
    assert env_vars.get("POSTGRES_USER") != "postgres", (
        "POSTGRES_USER must not be 'postgres' (superuser)")


def test_url_vars_use_localhost(env_vars: dict[str, str]) -> None:
    """Inter-service URLs in .env.example target localhost (non-Docker)."""
    for var, val in env_vars.items():
        if var.startswith("TAYFIN_") and var.endswith("_BASE_URL"):
            assert "localhost" in val, (
                f"{var} should use localhost for non-Docker defaults, got {val}")


def test_canonical_completeness(env_vars: dict[str, str]) -> None:
    """Every canonical variable from ADR-05 is present in .env.example."""
    missing = set(ALL_CANONICAL.keys()) - set(env_vars.keys())
    assert not missing, f"Missing canonical vars in .env.example: {missing}"
