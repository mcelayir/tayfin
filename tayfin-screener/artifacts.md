<!--
Artifact inventory for E36-05.1 — collected sources and authoritative locations
Generated: 2026-03-29
Owner: @dev
-->
# tayfin-screener — Artifacts & authoritative references

Summary: primary repo-relative paths for `tayfin-screener` used to author READMEs and extract canonical payload shapes.

- Top-level
  - tayfin-screener/README.md — (create/update to canonical template)

- API
  - tayfin-screener/tayfin-screener-api/README.md — API README (review existing content)
  - tayfin-screener/tayfin-screener-api/src/tayfin_screener_api/app.py — API handlers / route defs
  - tayfin-screener/tayfin-screener-api/src/tayfin_screener_api/repositories/vcp_repository.py
  - tayfin-screener/tayfin-screener-api/src/tayfin_screener_api/repositories/mcsa_repository.py
  - tayfin-screener/tayfin-screener-api/config/screener.yml — API YAML config
  - tayfin-screener/tayfin-screener-api/scripts/run_api.sh

- Jobs
  - tayfin-screener/tayfin-screener-jobs/README.md — jobs README (review)
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/cli/main.py — Typer CLI
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/jobs/vcp_screen_job.py
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/jobs/mcsa_screen_job.py
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/clients/ingestor_client.py
  - tayfin-screener/tayfin-screener-jobs/config/screener.yml

- Screening logic
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/vcp/* (contraction_detection, swing_detection, volume_features)
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/mcsa/* (scoring, volume_assessment)

- DB & migrations
  - tayfin-screener/db/migrations/V1__init_audit.sql
  - tayfin-screener/db/migrations/V2__create_vcp_results.sql
  - tayfin-screener/db/migrations/V3__create_mcsa_results.sql

- Repositories & persistence
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/mcsa/repositories/mcsa_result_repository.py
  - tayfin-screener/tayfin-screener-jobs/src/tayfin_screener_jobs/vcp/repositories/vcp_result_repository.py

- Tests
  - tayfin-screener/tayfin-screener-jobs/tests/* (mcsa, vcp, scoring, detection)
  - tayfin-screener/tayfin-screener-api/tests/*

Notes and next steps for E36-05.1:
- Extract canonical request/response shapes from `app.py` and `repositories/*_repository.py` for schema generation.  
- Review `config/screener.yml` for env var references and CLI patterns.  
- Draft top-level README using canonical template and link API/jobs READMEs.
