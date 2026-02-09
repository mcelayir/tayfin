Tayfin ingestor jobs (Phase 3 skeleton)

This package contains a minimal blueprint for the discovery job: CLI, config loader,
provider factory (placeholder), SQLAlchemy Core repositories, and job composition root.

Run locally (from repo root):

  python -m tayfin_ingestor_jobs jobs list --config tayfin-ingestor/tayfin-ingestor-jobs/config/discovery.yml
Purpose: Ephemeral ingestion jobs (run-once tasks).
Phase: Phase 1 skeleton (no business logic yet).
Context: tayfin-ingestor
