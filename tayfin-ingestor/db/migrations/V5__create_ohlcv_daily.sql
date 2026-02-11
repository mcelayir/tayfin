-- Flyway migration: create ohlcv_daily time-series table
-- V5__create_ohlcv_daily.sql
--
-- Stores one canonical daily OHLCV candle per instrument per day.
-- Unique on (instrument_id, as_of_date) — source changes overwrite via upsert.

CREATE SCHEMA IF NOT EXISTS tayfin_ingestor;

CREATE TABLE IF NOT EXISTS tayfin_ingestor.ohlcv_daily (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instrument_id uuid NOT NULL,
  as_of_date date NOT NULL,

  open numeric(18,6) NOT NULL,
  high numeric(18,6) NOT NULL,
  low numeric(18,6) NOT NULL,
  close numeric(18,6) NOT NULL,
  volume bigint NOT NULL,

  source text NOT NULL,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by_job_run_id uuid NOT NULL,
  updated_by_job_run_id uuid NULL,

  CONSTRAINT uq_ohlcv_daily_instrument_date UNIQUE (instrument_id, as_of_date),

  CONSTRAINT fk_ohlcv_daily_instrument FOREIGN KEY (instrument_id) REFERENCES tayfin_ingestor.instruments (id) ON DELETE CASCADE,
  CONSTRAINT fk_ohlcv_daily_created_job_run FOREIGN KEY (created_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE RESTRICT,
  CONSTRAINT fk_ohlcv_daily_updated_job_run FOREIGN KEY (updated_by_job_run_id) REFERENCES tayfin_ingestor.job_runs (id) ON DELETE SET NULL
);

CREATE INDEX idx_ohlcv_instrument_date ON tayfin_ingestor.ohlcv_daily (instrument_id, as_of_date);
CREATE INDEX idx_ohlcv_date ON tayfin_ingestor.ohlcv_daily (as_of_date);
