-- Flyway migration: create discovery tables for tayfin_ingestor
-- V2__create_discovery_tables.sql

-- Ensure schema exists (should exist from V1, but safe to include)
CREATE SCHEMA IF NOT EXISTS tayfin_ingestor;

-- instruments: store known instruments/tickers discovered by ingestor processes
CREATE TABLE IF NOT EXISTS tayfin_ingestor.instruments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker text NOT NULL,
  country text NOT NULL,
  instrument_type text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by_job_run_id uuid NOT NULL,
  updated_by_job_run_id uuid NULL,
  CONSTRAINT uq_tayfin_ingestor_instruments_ticker_country UNIQUE (ticker, country),
  CONSTRAINT fk_tayfin_ingestor_instruments_created_job_run FOREIGN KEY (created_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE RESTRICT,
  CONSTRAINT fk_tayfin_ingestor_instruments_updated_job_run FOREIGN KEY (updated_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_instruments_ticker ON tayfin_ingestor.instruments (ticker);
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_instruments_country ON tayfin_ingestor.instruments (country);

-- index_memberships: map indices to instruments
CREATE TABLE IF NOT EXISTS tayfin_ingestor.index_memberships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  index_code text NOT NULL,
  instrument_id uuid NOT NULL,
  country text NOT NULL,
  effective_date date NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by_job_run_id uuid NOT NULL,
  updated_by_job_run_id uuid NULL,
  CONSTRAINT uq_tayfin_ingestor_index_memberships_index_instrument UNIQUE (index_code, instrument_id),
  CONSTRAINT fk_tayfin_ingestor_index_memberships_instrument FOREIGN KEY (instrument_id) REFERENCES tayfin_ingestor.instruments (id) ON DELETE CASCADE,
  CONSTRAINT fk_tayfin_ingestor_index_memberships_created_job_run FOREIGN KEY (created_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE RESTRICT,
  CONSTRAINT fk_tayfin_ingestor_index_memberships_updated_job_run FOREIGN KEY (updated_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_index_memberships_index_code ON tayfin_ingestor.index_memberships (index_code);
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_index_memberships_instrument_id ON tayfin_ingestor.index_memberships (instrument_id);
