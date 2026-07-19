---
title: Configuration
description: Server flags, environment variables, storage backends, and runtime settings.
---

Atomic has two kinds of configuration:

- **Server configuration** - command-line flags and environment variables that control how `atomic-server` starts.
- **Runtime settings** - key-value settings stored in the registry or data database and editable through the UI/API.

## Command-Line Options

```bash
atomic-server [GLOBAL_OPTIONS] <COMMAND>

Global options:
  --data-dir <path>       Directory containing registry.db and data databases
  --db-path <path>        Deprecated; use --data-dir

Commands:
  serve                   Start the HTTP server
  token                   Manage API tokens
```

## Serve Options

```bash
atomic-server --data-dir ./data serve \
  --bind 0.0.0.0 \
  --port 8080 \
  --public-url https://atomic.example.com \
  --setup-token "$ATOMIC_SETUP_TOKEN"
```

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--port` | | `8080` | Port to listen on |
| `--bind` | | `127.0.0.1` | Address to bind to |
| `--public-url` | `PUBLIC_URL` | unset | Public URL used for OAuth/MCP discovery |
| `--storage` | `ATOMIC_STORAGE` | `sqlite` | Storage backend: `sqlite` or `postgres` |
| `--database-url` | `ATOMIC_DATABASE_URL` | unset | Postgres connection string when using Postgres |
| `--setup-token` | `ATOMIC_SETUP_TOKEN` | unset | Token required to claim a fresh instance through the setup UI |
| `--dangerously-skip-setup-token` | `ATOMIC_DANGEROUSLY_SKIP_SETUP_TOKEN` | `false` | Insecurely allow first-run setup claims without a setup token |

Use `--bind 0.0.0.0` only when the server should accept connections from outside the host or container network. Put it behind a reverse proxy for public deployments.
Set `ATOMIC_SETUP_TOKEN` before using the setup UI on a fresh server:

```bash
export ATOMIC_SETUP_TOKEN="$(openssl rand -base64 24)"
```

`--dangerously-skip-setup-token` is intended only for trusted development environments. With that flag enabled, any client that can reach an unclaimed server can claim it.

## Token Command Options

The token command must point at the same data directory or storage backend as the server:

```bash
atomic-server --data-dir ./data token create --name "my-laptop"
atomic-server --data-dir ./data token list
atomic-server --data-dir ./data token revoke <token-id>
```

For Postgres:

```bash
ATOMIC_STORAGE=postgres \
ATOMIC_DATABASE_URL=postgres://user:pass@host:5432/atomic \
atomic-server token list
```

## Runtime Settings

Runtime settings are available through:

- The Settings UI
- `GET /api/settings`
- `PUT /api/settings/{key}`
- SQLite/Postgres direct inspection for operators

Important settings include:

| Key | Purpose |
|-----|---------|
| `provider` | `openrouter`, `ollama`, or OpenAI-compatible provider selection |
| `embedding_model` | OpenRouter embedding model |
| `tagging_model` | OpenRouter tagging model |
| `wiki_model` | Wiki and briefing model |
| `chat_model` | Chat model |
| `auto_tagging_enabled` | Enables or disables automatic tagging |
| `ollama_host` | Ollama server URL |
| `openai_compat_base_url` | OpenAI-compatible API base URL |
| `task.daily_briefing.enabled` | Enables scheduled briefings |
| `task.daily_briefing.interval_hours` | Briefing interval |
| `task.draft_pipeline.enabled` | Enables scheduled draft pipeline processing |

Inspect SQLite settings:

```bash
sqlite3 databases/registry.db "SELECT key, value FROM settings;"
```

## Registry vs Data Databases

Atomic uses a registry database plus one or more data databases. Global settings and API tokens live in the registry. Atoms, tags, chunks, wiki articles, conversations, feeds, and briefings live in data databases.

For multi-database deployments, background jobs and per-database state are isolated by database. See [Multi-Database](/guides/multi-database/).

## Health and Docs

Public endpoints useful for operations:

- `GET /health`
- `GET /api/docs`
- `GET /api/docs/openapi.json`

Authenticated status endpoints:

- `GET /api/embeddings/status`
- `GET /api/embeddings/status/all`
- `GET /api/logs`

## Related

- [Docker Compose](/self-hosting/docker-compose/)
- [Token Management](/self-hosting/token-management/)
- [Data and Backups](/self-hosting/data-and-backups/)
