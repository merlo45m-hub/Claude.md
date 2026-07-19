---
title: Data and Backups
description: Understand Atomic's database files, exports, and backup options.
---

Atomic stores persistent data in the configured data directory or Docker volume.

## SQLite Layout

For SQLite deployments, the data directory contains:

```text
databases/
  registry.db
  default.db
  <database-id>.db
```

The registry stores global metadata such as API tokens, settings, and database records. Each data database stores atoms, tags, chunks, embeddings, wiki articles, chats, feeds, briefings, semantic edges, and canvas positions.

## Desktop Data Location

The desktop app uses platform-specific application data directories:

- macOS: `~/Library/Application Support/com.atomic.app/`
- Linux: `~/.local/share/com.atomic.app/`

The desktop sidecar also stores a local server token and PID file in the app data directory.

## Docker Data Location

The default compose file stores data in the `atomic-data` Docker volume.

```bash
docker volume inspect atomic_atomic-data
```

The exact volume name depends on your compose project name.

## Markdown Exports

Start an export for a database:

```bash
curl -X POST http://localhost:8080/api/databases/<db-id>/exports/markdown \
  -H "Authorization: Bearer <token>"
```

Poll the export job:

```bash
curl http://localhost:8080/api/exports/<job-id> \
  -H "Authorization: Bearer <token>"
```

When complete, the response includes a temporary `download_path`. The download token expires after a short time, so download promptly.

Cancel or delete a job:

```bash
curl -X DELETE http://localhost:8080/api/exports/<job-id> \
  -H "Authorization: Bearer <token>"
```

## Backup Guidance

- Stop the server or use SQLite-safe backup tooling before copying live `.db` files.
- Back up the whole data directory or Docker volume, not just `default.db`.
- Include `registry.db`; otherwise API tokens and database metadata are missing.
- For multi-database deployments, include every `*.db` file.
- If using the optional Litestream compose profile, test restore before relying on it.

## Related

- [Multi-Database](/guides/multi-database/)
- [Docker Compose](/self-hosting/docker-compose/)
- [Token Management](/self-hosting/token-management/)
