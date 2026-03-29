#!/usr/bin/env python3
"""Validate screener README example payloads against local JSON Schemas.

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
EXAMPLES_DIR = ROOT / "examples"

schemas = {
    "screener_result_latest": json.loads((SCHEMA_DIR / "screener_result_latest.json").read_text()),
    "screener_result_range": json.loads((SCHEMA_DIR / "screener_result_range.json").read_text()),
    "persisted_screener_result": json.loads((SCHEMA_DIR / "persisted_screener_result.json").read_text()),
}

examples = {
    "screener_result_latest": json.loads((EXAMPLES_DIR / "screener_result_latest.example.json").read_text()),
    "screener_result_range": json.loads((EXAMPLES_DIR / "screener_result_range.example.json").read_text()),
    "persisted_screener_result": json.loads((EXAMPLES_DIR / "persisted_screener_result.example.json").read_text()),
}

results = []
for name, schema in schemas.items():
    ex = examples.get(name)
    try:
        # Resolve relative $ref by setting the base URI to the schema directory
        resolver = None
        try:
            resolver = jsonschema.RefResolver(base_uri=SCHEMA_DIR.as_uri() + "/", referrer=schema)
        except Exception:
            resolver = None
        if resolver:
            jsonschema.validate(instance=ex, schema=schema, resolver=resolver)
        else:
            jsonschema.validate(instance=ex, schema=schema)
        results.append((name, True, "OK"))
    except jsonschema.ValidationError as ve:
        results.append((name, False, str(ve)))

print(json.dumps({"validations": [
    {"schema": r[0], "ok": r[1], "message": r[2]} for r in results
]}, indent=2))

sys.exit(0 if all(r[1] for r in results) else 2)
