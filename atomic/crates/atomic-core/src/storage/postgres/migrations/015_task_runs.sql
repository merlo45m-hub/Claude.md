-- Per-DB ledger of scheduled-task executions. Reports (phase 2) will be the
-- first writer; phase 1.5 ships the table + helpers dormant so the claim /
-- lease / crash-recovery semantics are exercised by tests before any
-- production caller depends on them.
--
-- Column types mirror the rest of this Postgres schema: TEXT for timestamps
-- (stored as RFC3339 UTC, lexicographically comparable) and TEXT for the
-- JSON scope snapshot. That keeps SQLite and Postgres trivially symmetric on
-- the storage boundary; structured-JSON access lives at the Rust layer.
-- The `db_id` column scopes runs to a logical database when multiple DBs
-- share the same Postgres pool — mirroring every other per-DB table here.
-- See docs/plans/reports.md §"Execution ledger — task_runs" for the
-- state-machine, backoff, and crash-recovery contract this schema supports.
CREATE TABLE IF NOT EXISTS task_runs (
    id              TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL,
    subject_id      TEXT,
    state           TEXT NOT NULL DEFAULT 'pending',
    trigger         TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    lease_until     TEXT,
    next_attempt_at TEXT NOT NULL,
    scope           TEXT,
    result_id       TEXT,
    last_error      TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    db_id           TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_task_runs_claim
    ON task_runs(db_id, state, next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_task_runs_lease
    ON task_runs(db_id, state, lease_until);
CREATE INDEX IF NOT EXISTS idx_task_runs_history
    ON task_runs(db_id, task_id, subject_id, created_at);

INSERT INTO schema_version (version) VALUES (15);
