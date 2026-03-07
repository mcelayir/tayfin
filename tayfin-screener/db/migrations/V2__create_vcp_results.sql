-- V2: Create vcp_results table
-- Stores per-ticker, per-date VCP screening output with score, confidence,
-- and full feature evidence in JSONB.

CREATE TABLE IF NOT EXISTS tayfin_screener.vcp_results (
    id                      uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                  text          NOT NULL,
    instrument_id           uuid          NULL,
    as_of_date              date          NOT NULL,
    vcp_score               numeric       NOT NULL,
    vcp_confidence          text          NULL,
    pattern_detected        boolean       NOT NULL DEFAULT false,
    features_json           jsonb         NOT NULL DEFAULT '{}'::jsonb,

    -- audit / provenance
    created_at              timestamptz   NOT NULL DEFAULT now(),
    updated_at              timestamptz   NOT NULL DEFAULT now(),
    created_by_job_run_id   uuid          NOT NULL,
    updated_by_job_run_id   uuid          NULL,

    CONSTRAINT fk_vcp_results_created_by
        FOREIGN KEY (created_by_job_run_id)
        REFERENCES tayfin_screener.job_runs (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_vcp_results_updated_by
        FOREIGN KEY (updated_by_job_run_id)
        REFERENCES tayfin_screener.job_runs (id)
        ON DELETE SET NULL,

    -- natural key: one VCP result per ticker per date (idempotent upsert)
    CONSTRAINT uq_vcp_results_natural_key
        UNIQUE (ticker, as_of_date)
);

-- Primary query pattern: latest result for a ticker
CREATE INDEX IF NOT EXISTS idx_vcp_results_ticker_date
    ON tayfin_screener.vcp_results (ticker, as_of_date DESC);

-- Scan by date (index-wide daily results)
CREATE INDEX IF NOT EXISTS idx_vcp_results_as_of_date
    ON tayfin_screener.vcp_results (as_of_date DESC);

-- Filter detected patterns efficiently
CREATE INDEX IF NOT EXISTS idx_vcp_results_detected_date
    ON tayfin_screener.vcp_results (pattern_detected, as_of_date DESC);
