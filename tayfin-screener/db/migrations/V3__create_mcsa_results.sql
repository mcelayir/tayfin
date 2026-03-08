-- V3: Create mcsa_results table
-- Stores per-ticker, per-date MCSA (Mark Minervini Trend Template) screening
-- output with per-criterion pass/fail breakdown, RS ranking, and score count.
-- See ADR-0001-mcsa-trend-template.md for architectural decisions.

CREATE TABLE IF NOT EXISTS tayfin_screener.mcsa_results (
    id                      uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker                  text          NOT NULL,
    instrument_id           uuid          NULL,
    as_of_date              date          NOT NULL,
    mcsa_pass               boolean       NOT NULL DEFAULT false,
    criteria_json           jsonb         NOT NULL DEFAULT '{}'::jsonb,
    rs_rank                 numeric       NOT NULL,
    criteria_count_pass     smallint      NOT NULL DEFAULT 0,

    -- audit / provenance
    created_at              timestamptz   NOT NULL DEFAULT now(),
    updated_at              timestamptz   NOT NULL DEFAULT now(),
    created_by_job_run_id   uuid          NOT NULL,
    updated_by_job_run_id   uuid          NULL,

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

-- Filter passing stocks efficiently
CREATE INDEX IF NOT EXISTS idx_mcsa_results_pass_date
    ON tayfin_screener.mcsa_results (mcsa_pass, as_of_date DESC);

-- Sort/filter by criteria count
CREATE INDEX IF NOT EXISTS idx_mcsa_results_criteria_count
    ON tayfin_screener.mcsa_results (criteria_count_pass DESC, as_of_date DESC);
