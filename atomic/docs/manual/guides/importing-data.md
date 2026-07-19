---
title: Importing Data
description: Import markdown folders, Obsidian vaults, Apple Notes, URLs, and feed content into Atomic.
---

Atomic supports several capture and import paths. Choose the path that matches where your data currently lives.

## Markdown Folders and Obsidian Vaults

The desktop app includes a folder importer for markdown files. It is commonly used with Obsidian vaults.

The importer:

- Imports markdown files as atoms
- Preserves Obsidian-style `[[wikilinks]]`
- Can turn folders/frontmatter tags into Atomic tags
- Excludes common non-note directories such as `.obsidian`, `.trash`, `.git`, and `node_modules`
- Uses source URLs such as `obsidian://VaultName/path/to/note` for deduplication

From the UI, use the import/capture options and choose a folder.

From scripts in a local checkout:

```bash
npm run import:obsidian /path/to/vault
npm run import:obsidian /path/to/vault -- --max 100
npm run import:obsidian /path/to/vault -- --dry-run
npm run import:obsidian /path/to/vault -- --exclude "Templates/**"
```

The server API also exposes:

```bash
curl -X POST http://localhost:8080/api/import/obsidian \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vault_path": "/path/to/vault", "max_notes": 100}'
```

Server-side import paths must exist on the server machine.

## Apple Notes

The desktop app includes an Apple Notes importer on macOS. It reads the local Apple Notes database, converts notes to markdown, and can turn Apple Notes folders into tags.

Apple Notes import requires **Full Disk Access** so Atomic can read the Notes database. This is desktop-only and does not apply to a remote headless server.

## URL Ingestion

Use URL ingestion when you want Atomic to fetch and extract an article:

```bash
curl -X POST http://localhost:8080/api/ingest/url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "tag_ids": [],
    "title_hint": null,
    "published_at": null
  }'
```

Batch ingestion:

```bash
curl -X POST http://localhost:8080/api/ingest/urls \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      { "url": "https://example.com/one", "tag_ids": [] },
      { "url": "https://example.com/two", "tag_ids": [] }
    ]
  }'
```

URL ingestion emits WebSocket events such as `ingestion-fetch-started`, `ingestion-complete`, and `ingestion-failed`.

## RSS and Atom Feeds

Use feeds when you want Atomic to poll a source repeatedly and create atoms for new entries. See [URL Ingestion and Feeds](/guides/url-ingestion-and-feeds/) for details.

## Wikipedia Import Script

The repository includes a Wikipedia import script for stress testing and demo data:

```bash
npm run import:wikipedia -- "Machine Learning" "Rust (programming language)"
```

Treat this as a developer utility rather than the main user import flow.

## After Import

Imports create atoms immediately and then the background pipeline handles embeddings, tagging, and graph updates. Check progress with:

```bash
curl http://localhost:8080/api/embeddings/status \
  -H "Authorization: Bearer <token>"
```

## Related

- [Atoms](/concepts/atoms/)
- [URL Ingestion and Feeds](/guides/url-ingestion-and-feeds/)
- [AI Providers](/getting-started/ai-providers/)
