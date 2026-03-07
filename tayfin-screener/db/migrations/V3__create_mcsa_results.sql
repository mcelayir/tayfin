-- V3: Create mcsa_results table
-- Stores per-ticker, per-date MCSA (Minervini Chartist Scoring Algorithm) output
-- with composite score, band classification, per-component scores, and full
-- evidence payload in JSONB.

CREATE TABLE IF NOT EXISTS tayfin_screener.mcsa_results (
    id                        uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                    text          NOT NULL,
    instrument_id             uuid          NULL,
    as_of_date                date          NOT NULL,

    -- composite score (0–100)
    mcsa_score                numeric       NOT NULL,

    -- band classification: strong / watchlist / neutral / weak
    mcsa_band                 text          NOT NULL,

    -- per-component scores (stored separately for fast queries)
    trend_score               numeric       NOT NULL DEFAULT 0,
    vcp_component             numeric       NOT NULL DEFAULT 0,
    volume_score              numeric       NOT NULL DEFAULT 0,
    fundamental_score         numeric       NOT NULL DEFAULT 0,

    -- full evidence object (raw values + rule outcomes per ADR-01)
    evidence_json             jsonb         NOT NULL DEFAULT '{}'::jsonb,

    -- fields that were missing during scoring (partial mode)
    missing_fields            jsonb         NOT NULL DEFAULT '[]'::jsonb,

    -- audit / provenance
    created_at                timestamptz   NOT NULL DEFAULT now(),
    updated_at                timestamptz   NOT NULL DEFAULT now(),
    created_by_job_run_id     uuid          NOT NULL,
    updated_by_job_run_id     uuid          NULL,

    CONSTRAINT fk_mcsa_results_created_by
        FOREIGN KEY (created_by_job_run_id)
        REFERENCES tayfin_screener.job_runs (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mcsa_results_updated_by
        FOREIGN KEY (updated_by_job_run_id)
        REFERENCES tayfin_screener.job_runs (id)
        ON DELETE SET NULL,

    -- natural key: one MCSA result per ticker per date (idempotent upsert)
    CONSTRAINT uq_mcsa_results_natural_key
        UNIQUE (ticker, as_of_date)
);

-- Primary query pattern: latest result for a ticker
CREATE INDEX IF NOT EXISTS idx_mcsa_results_ticker_date
    ON tayfin_screener.mcsa_results (ticker, as_of_date DESC);

-- Scan by date (index-wide daily results)
CREATE INDEX IF NOT EXISTS idx_mcsa_results_as_of_date
    ON tayfin_screener.mcsa_results (as_of_date DESC);

-- Filter by band efficiently
CREATE INDEX IF NOT EXISTS idx_mcsa_results_band_date
    ON tayfin_screener.mcsa_results (mcsa_band, as_of_date DESC);
