-- V3: Create job_run_items audit table
-- Tracks per-item results within a job run

CREATE TABLE IF NOT EXISTS tayfin_indicator.job_run_items (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_run_id        uuid        NOT NULL,
    item_key          text        NOT NULL,
    status            text        NOT NULL,
    message           text        NULL,
    details           jsonb       NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_indicator_job_run
        FOREIGN KEY (job_run_id)
        REFERENCES tayfin_indicator.job_runs (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_indicator_job_run_item
        UNIQUE (job_run_id, item_key)
);

CREATE INDEX idx_indicator_job_run_items_job_run_id ON tayfin_indicator.job_run_items (job_run_id);
CREATE INDEX idx_indicator_job_run_items_item_key   ON tayfin_indicator.job_run_items (item_key);
CREATE INDEX idx_indicator_job_run_items_status     ON tayfin_indicator.job_run_items (status);
