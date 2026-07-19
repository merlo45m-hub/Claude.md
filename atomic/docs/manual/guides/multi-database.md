---
title: Multi-Database
description: Manage multiple Atomic knowledge bases under one server.
---

Atomic can host multiple knowledge bases under one server process. A registry database stores shared metadata and API tokens, while each data database stores its own atoms, tags, chunks, embeddings, wiki articles, conversations, positions, feeds, and briefings.

## Active vs Default Database

- **Active database** - the database used when a request does not specify a database.
- **Default database** - the database the server should prefer as the default choice.
- **Explicit database** - a request can target a database with `X-Atomic-Database: <id>` or `?db=<id>`.

The web UI and iOS app can switch databases. Integrations should pass an explicit database when they should not depend on server active state.

## API

List databases:

```bash
curl http://localhost:8080/api/databases \
  -H "Authorization: Bearer <token>"
```

Create and rename:

```bash
curl -X POST http://localhost:8080/api/databases \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Research"}'

curl -X PUT http://localhost:8080/api/databases/<db-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Research Archive"}'
```

Activate or set default:

```bash
curl -X PUT http://localhost:8080/api/databases/<db-id>/activate \
  -H "Authorization: Bearer <token>"

curl -X PUT http://localhost:8080/api/databases/<db-id>/default \
  -H "Authorization: Bearer <token>"
```

Target a request explicitly:

```bash
curl "http://localhost:8080/api/atoms?limit=20" \
  -H "Authorization: Bearer <token>" \
  -H "X-Atomic-Database: <db-id>"
```

## Exports

Start a markdown export for one database:

```bash
curl -X POST http://localhost:8080/api/databases/<db-id>/exports/markdown \
  -H "Authorization: Bearer <token>"
```

Check job status:

```bash
curl http://localhost:8080/api/exports/<job-id> \
  -H "Authorization: Bearer <token>"
```

Completed jobs return a temporary `download_path`. The download token is short-lived, so fetch the artifact promptly.

## Operational Notes

- API tokens are managed in the registry and can access databases unless your deployment adds its own network or proxy controls.
- Background jobs such as feed polling and briefings run per database.
- Per-database pipeline status is available at `GET /api/embeddings/status/all`.
- The desktop app stores local databases in its application data directory; self-hosted SQLite deployments store them under the configured data directory.

## Related

- [Token Management](/self-hosting/token-management/)
- [Data and Backups](/self-hosting/data-and-backups/)
- [API Overview](/api/overview/)
