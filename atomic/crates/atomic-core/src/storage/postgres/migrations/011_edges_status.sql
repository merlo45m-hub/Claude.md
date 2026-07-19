-- Track semantic edge computation status per atom.
--
-- SQLite added this in its V10 migration, but Postgres did not. Graph
-- maintenance depends on this column for claiming pending edge work.

ALTER TABLE atoms
ADD COLUMN IF NOT EXISTS edges_status TEXT NOT NULL DEFAULT 'pending';

CREATE INDEX IF NOT EXISTS idx_atoms_edges_status
    ON atoms(edges_status);

UPDATE atoms
SET edges_status = 'pending'
WHERE embedding_status = 'complete';

UPDATE atoms
SET edges_status = 'none'
WHERE embedding_status != 'complete';

INSERT INTO schema_version (version) VALUES (11);
