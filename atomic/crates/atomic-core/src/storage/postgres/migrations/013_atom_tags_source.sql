-- Track whether an atom_tags row was created by the auto-tagger or by an
-- explicit user/import action. The "Re-tag all atoms" feature deletes only
-- 'auto'-source rows whose tag has no wiki article. Existing rows default to
-- 'auto' (the realistic majority case for a corpus that has run through the
-- background tagger).
--
-- Note: SQLite snapshots a per-DB legacy count into its per-DB settings table
-- so the UI can warn that pre-upgrade rows are being treated as auto. The
-- Postgres backend has a single shared settings table (no per-DB scope), so
-- the snapshot is omitted here; the pipeline-status query reports 0 and the
-- UI just won't show that secondary warning on Postgres deployments.
ALTER TABLE atom_tags ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'auto';

INSERT INTO schema_version (version) VALUES (13);
