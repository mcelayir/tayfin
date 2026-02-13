-- V4: Create indicator_series table
-- Generic, extensible storage for computed indicator time-series

CREATE TABLE IF NOT EXISTS tayfin_indicator.indicator_series (
    id                      uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id           uuid          NULL,
    ticker                  text          NOT NULL,
    as_of_date              date          NOT NULL,
    indicator_key           text          NOT NULL,
    params_json             jsonb         NOT NULL DEFAULT '{}'::jsonb,
    value                   numeric       NOT NULL,
    source                  text          NOT NULL DEFAULT 'computed',

    -- audit
    created_at              timestamptz   NOT NULL DEFAULT now(),
    updated_at              timestamptz   NOT NULL DEFAULT now(),
    created_by_job_run_id   uuid          NOT NULL,
    updated_by_job_run_id   uuid          NULL,

    CONSTRAINT fk_indicator_series_created_by
        FOREIGN KEY (created_by_job_run_id)
        REFERENCES tayfin_indicator.job_runs (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_indicator_series_updated_by
        FOREIGN KEY (updated_by_job_run_id)
        REFERENCES tayfin_indicator.job_runs (id)
        ON DELETE SET NULL,

    CONSTRAINT uq_indicator_series_natural_key
        UNIQUE (ticker, as_of_date, indicator_key, params_json)
);

-- Query indexes
CREATE INDEX idx_indicator_series_ticker_key_date
    ON tayfin_indicator.indicator_series (ticker, indicator_key, as_of_date);

CREATE INDEX idx_indicator_series_indicator_key
    ON tayfin_indicator.indicator_series (indicator_key);

CREATE INDEX idx_indicator_series_as_of_date
    ON tayfin_indicator.indicator_series (as_of_date);
