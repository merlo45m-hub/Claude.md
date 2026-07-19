-- Migration 004: Wiki proposals (human-in-the-loop update review)
--
-- At most one pending proposal per article per database. Supersede via
-- ON CONFLICT (db_id, tag_id) DO UPDATE. Accept promotes to wiki_articles
-- (via the normal save path, which archives the prior version into
-- wiki_article_versions) and deletes the proposal row. Dismiss just deletes.

CREATE TABLE IF NOT EXISTS wiki_proposals (
    id              TEXT PRIMARY KEY,
    db_id           TEXT NOT NULL DEFAULT 'default',
    tag_id          TEXT NOT NULL,
    base_article_id TEXT NOT NULL,
    base_updated_at TEXT NOT NULL,
    content         TEXT NOT NULL,
    citations_json  TEXT NOT NULL,
    ops_json        TEXT NOT NULL,
    new_atom_count  INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- One proposal per (db_id, tag_id) — enables supersede via ON CONFLICT.
CREATE UNIQUE INDEX IF NOT EXISTS idx_wiki_proposals_db_tag
    ON wiki_proposals(db_id, tag_id);

CREATE INDEX IF NOT EXISTS idx_wiki_proposals_db_id
    ON wiki_proposals(db_id);

INSERT INTO schema_version (version) VALUES (4);
