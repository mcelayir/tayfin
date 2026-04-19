"""Config field completeness tests for BIST OHLCV targets.

Validates that config/ohlcv.yml and config/ohlcv_backfill.yml contain
correct, complete entries for the bist target.

No DB connection. No network calls. No environment variables required.
Runs offline with: pytest tests/test_bist_ohlcv_config.py -v
"""
import pytest

from tayfin_ingestor_jobs.config.loader import load_config

REQUIRED_OHLCV_FIELDS = ("code", "country", "index_code", "timeframe")
REQUIRED_BACKFILL_FIELDS = (
    "code",
    "country",
    "index_code",
    "timeframe",
    "default_exchange",
    "default_chunk_days",
    "window_days",
)


@pytest.fixture(scope="module")
def ohlcv_bist_cfg():
    cfg = load_config(default_filename="ohlcv.yml")
    return cfg["jobs"]["ohlcv"]["bist"]


@pytest.fixture(scope="module")
def ohlcv_backfill_bist_cfg():
    cfg = load_config(default_filename="ohlcv_backfill.yml")
    return cfg["jobs"]["bist"]


# ---------------------------------------------------------------------------
# ohlcv.yml — bist target
# ---------------------------------------------------------------------------


def test_bist_ohlcv_target_exists():
    cfg = load_config(default_filename="ohlcv.yml")
    target = cfg.get("jobs", {}).get("ohlcv", {}).get("bist")
    assert target is not None, "bist key missing under jobs.ohlcv in ohlcv.yml"
    assert isinstance(target, dict), "bist entry must be a dict"


def test_bist_ohlcv_required_fields(ohlcv_bist_cfg):
    missing = [f for f in REQUIRED_OHLCV_FIELDS if not ohlcv_bist_cfg.get(f)]
    assert not missing, f"bist ohlcv.yml is missing required fields: {missing}"


def test_bist_ohlcv_default_exchange(ohlcv_bist_cfg):
    assert ohlcv_bist_cfg.get("default_exchange") == "BIST", (
        "default_exchange must be 'BIST' in ohlcv.yml bist entry; "
        "without it the service falls back to the hardcoded 'NASDAQ' default"
    )


def test_bist_ohlcv_country_and_index_code(ohlcv_bist_cfg):
    assert ohlcv_bist_cfg["country"] == "TR", "country must be 'TR'"
    assert ohlcv_bist_cfg["index_code"] == "BIST", "index_code must be 'BIST'"


def test_bist_ohlcv_timeframe(ohlcv_bist_cfg):
    assert ohlcv_bist_cfg["timeframe"] == "1d", (
        "timeframe must be '1d' (lowercase); "
        "uppercase '1D' silently defaults to 1-minute in tradingview-scraper"
    )


# ---------------------------------------------------------------------------
# ohlcv_backfill.yml — bist target
# ---------------------------------------------------------------------------


def test_bist_backfill_target_exists():
    cfg = load_config(default_filename="ohlcv_backfill.yml")
    # Note: backfill targets sit directly under jobs, not jobs.ohlcv
    target = cfg.get("jobs", {}).get("bist")
    assert target is not None, (
        "bist key missing directly under jobs in ohlcv_backfill.yml; "
        "backfill targets are NOT nested under jobs.ohlcv_backfill"
    )
    assert isinstance(target, dict), "bist backfill entry must be a dict"


def test_bist_backfill_required_fields(ohlcv_backfill_bist_cfg):
    missing = [f for f in REQUIRED_BACKFILL_FIELDS if not ohlcv_backfill_bist_cfg.get(f)]
    assert not missing, f"bist ohlcv_backfill.yml is missing required fields: {missing}"


def test_bist_backfill_default_exchange(ohlcv_backfill_bist_cfg):
    assert ohlcv_backfill_bist_cfg.get("default_exchange") == "BIST", (
        "default_exchange must be 'BIST' in ohlcv_backfill.yml bist entry"
    )
