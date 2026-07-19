-- Reports (a coming primitive — see docs/plans/reports.md) emit finding
-- atoms that share the atoms table with user-captured notes. The `kind`
-- column lets every context-assembly query exclude or include report-
-- generated content explicitly. Existing rows default to 'captured', which
-- is the only kind any production write path currently produces.
ALTER TABLE atoms ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'captured';

CREATE INDEX IF NOT EXISTS idx_atoms_kind ON atoms(kind);

INSERT INTO schema_version (version) VALUES (14);
