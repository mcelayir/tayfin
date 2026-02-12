-- V2: Create job_runs audit table
-- Tracks each job execution for the tayfin_indicator context

CREATE TABLE IF NOT EXISTS tayfin_indicator.job_runs (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name          text        NOT NULL,
    target_name       text        NULL,
    status            text        NOT NULL,
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz NULL,
    params            jsonb       NULL,
    message           text        NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_indicator_job_runs_job_name   ON tayfin_indicator.job_runs (job_name);
CREATE INDEX idx_indicator_job_runs_status     ON tayfin_indicator.job_runs (status);
CREATE INDEX idx_indicator_job_runs_started_at ON tayfin_indicator.job_runs (started_at);
