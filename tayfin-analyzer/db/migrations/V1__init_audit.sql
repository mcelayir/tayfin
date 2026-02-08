-- Flyway migration: initialize audit foundation for tayfin_analyzer
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS tayfin_analyzer;

CREATE TABLE IF NOT EXISTS tayfin_analyzer.job_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_name text NOT NULL,
  trigger_type text NOT NULL,
  status text NOT NULL,
  started_at timestamptz NOT NULL,
  finished_at timestamptz NULL,
  items_total int DEFAULT 0,
  items_succeeded int DEFAULT 0,
  items_failed int DEFAULT 0,
  error_summary text NULL,
  error_details jsonb NULL,
  config jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tayfin_analyzer_job_runs_job_name_started_at ON tayfin_analyzer.job_runs (job_name, started_at DESC);

CREATE TABLE IF NOT EXISTS tayfin_analyzer.job_run_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_run_id uuid NOT NULL,
  item_key text NOT NULL,
  status text NOT NULL,
  error_summary text NULL,
  error_details jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_tayfin_analyzer_job_run FOREIGN KEY (job_run_id) REFERENCES tayfin_analyzer.job_runs (id) ON DELETE CASCADE,
  CONSTRAINT uq_tayfin_analyzer_job_run_item UNIQUE (job_run_id, item_key)
);

CREATE INDEX IF NOT EXISTS idx_tayfin_analyzer_job_run_items_job_run_id ON tayfin_analyzer.job_run_items (job_run_id);
