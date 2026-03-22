# E36-03.8 — Local Verification Report

Date: 2026-03-22
Branch: `docs/issue-36/st-01-placeholders`

Purpose
- Non-invasive local verification: validate illustrative README example payloads against the JSON Schemas added in E36-03.7.

What I ran
- Checked Python + `jsonschema` availability.
- Executed a small Python validator that:
  - Loads schema files from `tayfin-ingestor/tayfin-ingestor-api/schemas/`
  - Validates representative example payloads (from README) against each schema
  - Reports validation outcomes and schema validity

Commands executed (repro):
```bash
python -c "import sys, json, pkgutil
print('python', sys.version.split()[0])
try:
    import jsonschema
    print('jsonschema', jsonschema.__version__)
except Exception:
    print('jsonschema-missing')
"

python - <<'PY'
# (validator script used in this run — loads schemas and validates examples)
... (see repo .github/issues/36/e36-03-task-local-verification-report.md in branch for exact script)
PY
```

Results
- `jsonschema` found: 4.23.0
- Validation outcomes:
  - `fundamentals_latest`: OK
  - `fundamentals_list`: OK
  - `ohlcv_candle`: OK
  - `ohlcv_series`: OK
- Schema health: all four schema files pass `jsonschema` structural checks (no local schema errors).

Notes & Observations
- This verification does not start the API or run job scripts (no DB): it validates the README examples against the JSON Schema artifacts added under `tayfin-ingestor/tayfin-ingestor-api/schemas/`.
- The illustrative examples in the README validate successfully against the schemas after adjustments (E36-03.7 followups removed `as_of_date` requirement and made `from`/`to` optional for range responses).
- Next steps (optional):
  - Run the API locally and `curl` the endpoints to capture live responses and validate them against the schemas (requires DB + migrations).
  - Run job scripts with a local test DB to verify `JOB_RUN_ID` behavior and job writes (requires a safe test DB).

Attachments
- Script output was committed to branch and is visible in CI logs when run; summary above captures the run results.

Signed-off-by: @dev
