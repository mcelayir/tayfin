# E36-07 — Validation Results

Generated: 2026-03-29
Branch: `docs/issue-36/st-01-placeholders`

Summary: Ran JSON Schema validators for indicator, screener, and BFF modules. All example payloads validated successfully against their schemas.

## Indicator Validator Output
```
{
  "validations": [
    {"schema": "indicator_latest", "ok": true, "message": "OK"},
    {"schema": "indicator_range", "ok": true, "message": "OK"},
    {"schema": "indicator_index_latest", "ok": true, "message": "OK"},
    {"schema": "indicator_series", "ok": true, "message": "OK"}
  ]
}
```

## Screener Validator Output
```
{
  "validations": [
    {"schema": "screener_result_latest", "ok": true, "message": "OK"},
    {"schema": "screener_result_range", "ok": true, "message": "OK"},
    {"schema": "persisted_screener_result", "ok": true, "message": "OK"}
  ]
}
```

Notes: Screener validator emitted DeprecationWarnings related to `jsonschema.RefResolver` (benign; validator still passed).

## BFF Validator Output
```
{
  "validations": [
    {"schema": "mcsa_result", "ok": true, "message": "OK"},
    {"schema": "mcsa_dashboard", "ok": true, "message": "OK"}
  ]
}
```

## Next steps
- @lead-dev: review these results in the PR and proceed with E36-07 review tasks.
- If you want, I can post these results as a PR comment and tag `@lead-dev` and `@qa`.
