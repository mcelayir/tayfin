-- Flyway migration: create fundamentals_snapshots time-series table
-- V3__create_fundamentals_snapshots.sql
--
-- NOTE: Using numeric(24,8) for financial metrics to provide high precision
-- and large range for aggregated or scaled values. This follows guidance in
-- the Phase 4 task to prefer numeric(24,8).

CREATE SCHEMA IF NOT EXISTS tayfin_ingestor;

CREATE TABLE IF NOT EXISTS tayfin_ingestor.fundamentals_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL,
  as_of_date date NOT NULL,
  source text NOT NULL,

  price numeric(24,8) NULL,
  eps_ttm numeric(24,8) NULL,
  bvps numeric(24,8) NULL,
  standard_bvps numeric(24,8) NULL,
  total_debt numeric(24,8) NULL,
  total_equity numeric(24,8) NULL,
  net_income_ttm numeric(24,8) NULL,
  total_revenue numeric(24,8) NULL,
  pe_ratio numeric(24,8) NULL,
  pb_ratio numeric(24,8) NULL,
  standard_pb_ratio numeric(24,8) NULL,
  debt_equity numeric(24,8) NULL,
  roe numeric(24,8) NULL,
  net_margin numeric(24,8) NULL,
  revenue_growth_yoy numeric(24,8) NULL,
  earnings_growth_yoy numeric(24,8) NULL,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by_job_run_id uuid NOT NULL,
  updated_by_job_run_id uuid NULL,

  CONSTRAINT uq_tayfin_ingestor_fundamentals_snapshots_instrument_asof_source UNIQUE (instrument_id, as_of_date, source),

  CONSTRAINT fk_tayfin_ingestor_fundamentals_snapshots_instrument FOREIGN KEY (instrument_id) REFERENCES tayfin_ingestor.instruments (id) ON DELETE CASCADE,
  CONSTRAINT fk_tayfin_ingestor_fundamentals_snapshots_created_job_run FOREIGN KEY (created_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE RESTRICT,
  CONSTRAINT fk_tayfin_ingestor_fundamentals_snapshots_updated_job_run FOREIGN KEY (updated_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_fundamentals_snapshots_instrument_id ON tayfin_ingestor.fundamentals_snapshots (instrument_id);
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_fundamentals_snapshots_as_of_date ON tayfin_ingestor.fundamentals_snapshots (as_of_date);
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_fundamentals_snapshots_source ON tayfin_ingestor.fundamentals_snapshots (source);
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_fundamentals_snapshots_instrument_asof ON tayfin_ingestor.fundamentals_snapshots (instrument_id, as_of_date);
