-- Durable atom-level pipeline queue.
--
-- The queue coalesces work from create/update/import/retry/model-change paths
-- so workers can batch provider calls regardless of source.

CREATE TABLE IF NOT EXISTS atom_pipeline_jobs (
    atom_id TEXT NOT NULL,
    db_id TEXT NOT NULL DEFAULT 'default',
    embed_requested BOOLEAN NOT NULL DEFAULT FALSE,
    tag_requested BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NOT NULL,
    not_before TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    lease_until TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    atom_updated_at TEXT NOT NULL,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (atom_id, db_id)
);

CREATE INDEX IF NOT EXISTS idx_atom_pipeline_jobs_claim
    ON atom_pipeline_jobs(db_id, state, not_before, updated_at);
CREATE INDEX IF NOT EXISTS idx_atom_pipeline_jobs_lease
    ON atom_pipeline_jobs(db_id, state, lease_until);

INSERT INTO schema_version (version) VALUES (10);
