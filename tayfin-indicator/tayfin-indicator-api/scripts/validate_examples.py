#!/usr/bin/env python3
"""Validate README example payloads against local JSON Schemas.

Writes results to stdout in a machine-friendly format.
"""
import json
from pathlib import Path
import sys

try:
    import jsonschema
except Exception as e:
    print("jsonschema not available:", e, file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"

schemas = {
    "indicator_latest": json.loads((SCHEMA_DIR / "indicator_latest.json").read_text()),
    "indicator_range": json.loads((SCHEMA_DIR / "indicator_range.json").read_text()),
    "indicator_index_latest": json.loads((SCHEMA_DIR / "indicator_index_latest.json").read_text()),
    "indicator_series": json.loads((SCHEMA_DIR / "indicator_series.json").read_text()),
}

examples = {
    "indicator_latest": {
        "ticker": "AAPL",
        "as_of_date": "2026-02-12",
        "indicator": "sma",
        "params": {"window": 50},
        "value": 268.081,
        "source": "computed",
    },
    "indicator_range": {
        "ticker": "AAPL",
        "indicator": "sma",
        "params": {"window": 50},
        "from": "2025-01-01",
        "to": "2026-02-12",
        "items": [{"date": "2025-01-02", "value": 250.12}, {"date": "2025-01-03", "value": 251.34}],
    },
    "indicator_index_latest": {
        "index_code": "NDX",
        "indicator": "sma",
        "params": {"window": 50},
        "items": [{"ticker": "AAPL", "as_of_date": "2026-02-12", "value": 268.081}],
    },
    "indicator_series": {
        "ticker": "AAPL",
        "as_of_date": "2026-02-12",
        "indicator_key": "sma",
        "params_json": {"window": 50},
        "value": 268.081,
        "source": "computed",
    },
}

results = []
for name, schema in schemas.items():
    ex = examples.get(name)
    try:
        jsonschema.validate(instance=ex, schema=schema)
        results.append((name, True, "OK"))
    except jsonschema.ValidationError as ve:
        results.append((name, False, str(ve)))

print(json.dumps({"validations": [
    {"schema": r[0], "ok": r[1], "message": r[2]} for r in results
]}, indent=2))

sys.exit(0 if all(r[1] for r in results) else 2)
