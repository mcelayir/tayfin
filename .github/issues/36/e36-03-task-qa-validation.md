# E36-03 — QA Validation Report

Date: 2026-03-22
Branch: `docs/issue-36/st-01-placeholders`
Validator: @dev (performed by automated checks + manual inspection)

Summary
- I validated the `tayfin-ingestor` documentation produced under E36-03 for template conformance, env var coverage, example correctness, and runnable helpers.
- Outcome: PASS with minor actionable items (see Review Comments / Actionable Items).

What I validated (scope)
- Files inspected:
  - `tayfin-ingestor/README.md`
  - `tayfin-ingestor/tayfin-ingestor-api/README.md`
  - `tayfin-ingestor/tayfin-ingestor-jobs/README.md`
  - `tayfin-ingestor/tayfin-ingestor-api/schemas/*` (4 JSON Schema files)
  - `tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh`
- Checks performed:
  1. Template conformance: presence of required sections from canonical template (`Description`, `Service Overview`, `Getting Started` / `Local Commands`, `Environment Variables`, `Execution Examples`, `API Documentation` / `Schema Linkage`, `QA Checklist`).
  2. Env var coverage: presence of `JOB_RUN_ID` and DB connection vars in env var tables.
  3. Example payload validation: validate illustrative JSON examples against the JSON Schemas added in E36-03.7 using `jsonschema` (python).
  4. Executable helper verification: `run_api.sh` exists and is executable.

Steps executed (repro)
1. Confirmed presence of required README sections via a repository grep of section headers.
2. Re-ran the JSON Schema validator used in E36-03.8 against example payloads (and extracted JSON blocks from the API README). Command used (summary):

```bash
python -m pip install jsonschema
python - <<'PY'
# loads schemas from tayfin-ingestor/tayfin-ingestor-api/schemas
# extracts JSON blocks from tayfin-ingestor-api/README.md
# validates blocks that are valid JSON against the corresponding schema
PY
```

3. Checked `run_api.sh` file mode:

```bash
ls -l tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh
# -> -rwxr-xr-x (executable)
```

Results

1) Template conformance — Per-file results
- `tayfin-ingestor/README.md`: contains `Description`, `Service Overview`, `Getting Started`, `Environment Variables`, `Execution Examples`, `QA Checklist` — PASS
- `tayfin-ingestor/tayfin-ingestor-api/README.md`: contains `Getting Started`, `Environment Variables (API)`, `Endpoints`, `Schema Linkage`, `QA Checklist` — PASS
- `tayfin-ingestor/tayfin-ingestor-jobs/README.md`: contains `Getting Started`, `Environment Variables (jobs)`, `Jobs Overview`, `Execution Examples`, `QA Checklist` — PASS

2) Env var coverage
- All three READMEs include a dedicated env var table. `JOB_RUN_ID` is documented and called out clearly in jobs and top-level READMEs. In the API README `JOB_RUN_ID` is documented as optional (this is acceptable — API is read-only but may attach provenance when proxying to write paths). — PASS (coverage ok)

3) Example payload validation (JSON Schema)
- The JSON Schemas added under `tayfin-ingestor/tayfin-ingestor-api/schemas/` were validated for structural correctness (no schema errors).
- Example payloads extracted from `tayfin-ingestor/tayfin-ingestor-api/README.md` were validated where they were valid JSON. Validation outcomes:
  - `/fundamentals/latest` example — OK
  - `/fundamentals` range example — OK
  - `/ohlcv` latest/range examples — OK
  - Some README code blocks contain illustrative placeholders or `...` (not valid JSON); these were skipped and are marked `illustrative` in the README text. Recommendation: replace `...` placeholders with a clearly marked illustrative comment or a valid minimal sample where practical. — PARTIAL PASS

4) Executable helper
- `tayfin-ingestor/tayfin-ingestor-api/scripts/run_api.sh` exists and is executable (`-rwxr-xr-x`). It installs requirements from the API `requirements.txt` when present and runs the flask app on port 8000. — PASS

Overall result
- PASS with minor issues. Documentation meets the canonical template and includes schema linkage and env var tables. Example payloads validate against the provided JSON Schemas where examples are syntactically valid JSON. The repo contains a convenient `run_api.sh` to run the API locally.

Review Comments (observations worth addressing)
1. Several JSON code blocks in `tayfin-ingestor/tayfin-ingestor-api/README.md` contain `...` or truncated objects that are not valid JSON (these are illustrative). These blocks cause automated JSON extraction/validation to fail; they should either be:
   - Replaced with minimal valid JSON examples, or
   - Explicitly wrapped in a fenced block labeled `illustrative` and documented as not-for-validation.
2. Standardize `JOB_RUN_ID` guidance across READMEs: jobs/top-level currently mark `JOB_RUN_ID` as required; API marks as optional. This is functionally correct but worth a short note explaining the difference (jobs must set `JOB_RUN_ID` for writes; API may optionally accept/forward it). Add a one-line note in the API README clarifying this behavior.
3. Curl examples: consider adding explicit `-H 'Accept: application/json'` and host/port placeholders (e.g., `http://localhost:8000`) uniformly across examples for copy-paste usability.
4. Add a short sentence in each README pointing to `tayfin-ingestor/tayfin-ingestor-api/schemas/` and how to validate examples locally (example commands using `jsonschema` or `ajv`). The API README already links schemas — replicate the guidance in jobs/top-level README where applicable.

Actionable review items (priority order)
- A1: Replace or mark non-JSON illustrative blocks in API README. (owner: @dev) — high
- A2: Add a clarifying note about `JOB_RUN_ID` differences (owner: @dev) — medium
- A3: Add sample `jsonschema` validation command to API README and top-level README (owner: @dev) — low
- A4: Update curl examples to include `Accept: application/json` and explicit `localhost:8000` host for local dev (owner: @dev) — low

Files changed by QA (none) — QA did not modify docs; this report is informational and includes suggested edits.

Next steps
- Implement A1..A4 in a follow-up patch/PR and re-run this QA. If you'd like, I can implement A1..A4 now and open a draft PR on `docs/issue-36/st-01-placeholders` with the fixes.

Signed-off-by: @dev
