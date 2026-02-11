-- Flyway migration: add exchange column to instruments table
-- V4__add_exchange_to_instruments.sql

-- Add exchange column to instruments table
ALTER TABLE tayfin_ingestor.instruments
ADD COLUMN exchange text NULL;

-- Add index on exchange for efficient queries
CREATE INDEX IF NOT EXISTS idx_tayfin_ingestor_instruments_exchange ON tayfin_ingestor.instruments (exchange);