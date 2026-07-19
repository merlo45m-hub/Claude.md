---
title: MCP Server
description: Give AI agents long-term memory by connecting them to Atomic through the Model Context Protocol.
---

Atomic exposes an MCP server so AI agents can search, read, create, update, and ingest atoms. You can use it locally through the desktop app bridge or remotely through the self-hosted HTTP endpoint.

## Tools

Atomic exposes five MCP tools:

| Tool | What It Does |
|------|--------------|
| `semantic_search` | Hybrid keyword + semantic search over atoms, with optional `since_days` recency filtering |
| `read_atom` | Read full atom content by ID, with line-based pagination |
| `create_atom` | Store new markdown memory as an atom |
| `ingest_url` | Fetch a URL, extract article content, and save it as an atom |
| `update_atom` | Replace an existing atom's markdown content |

The server instructions tell agents to search before answering from memory, remember durable context, and update stale atoms instead of duplicating them.

`ingest_url` accepts a single `url` argument and returns the `atom_id`, source `url`, extracted `title`, `content_length`, and `already_exists`. If the URL already exists as an atom `source_url`, the tool returns the existing atom with `already_exists: true` instead of creating a duplicate.

## Desktop App: Local Bridge

The desktop app bundles `atomic-mcp-bridge`, a stdio-to-HTTP bridge. It reads the local sidecar connection automatically, so you do not need to create or paste a token. The bridge forwards MCP requests to Atomic's `/mcp` endpoint; tools are advertised by the server, so new server-side tools do not require bridge-specific configuration.

Open **Settings > Integrations > MCP Integration** in the desktop app for the exact bridge path.

Example for Claude Code, Claude Desktop, or any stdio MCP client:

```json
{
  "mcpServers": {
    "atomic": {
      "command": "/Applications/Atomic.app/Contents/MacOS/atomic-mcp-bridge"
    }
  }
}
```

On Windows the binary name is `atomic-mcp-bridge.exe`. On Linux the path depends on the installed package layout.

## Remote or Self-Hosted: Streamable HTTP

For self-hosted servers, connect to:

```text
https://your-server.example/mcp
```

Use a Bearer token:

```json
{
  "mcpServers": {
    "atomic": {
      "url": "https://your-server.example/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

Some clients use `"type": "url"` for HTTP MCP servers. If your client requires it, add that field to the `atomic` object.

## Create a Token

From the UI, create a dedicated token in Settings or the onboarding integration step.

From the CLI:

```bash
atomic-server --data-dir ./data token create --name "claude"
```

Save the raw token immediately. It is shown only once.

## Multi-Database

To target a specific database, add the `db` query parameter:

```text
https://your-server.example/mcp?db=<database-id>
```

Without `db`, MCP tools use the active database.

## OAuth and Public URL

Remote MCP OAuth discovery depends on `PUBLIC_URL` / `--public-url`. If this is not set, OAuth discovery endpoints return 404.

For self-hosted deployments:

```bash
PUBLIC_URL=https://atomic.example.com docker compose up -d
```

Your reverse proxy must pass:

- `/mcp`
- `/.well-known/oauth-authorization-server`
- `/.well-known/oauth-protected-resource`
- `/oauth/register`
- `/oauth/authorize`
- `/oauth/token`

## Suggested Agent Prompt

Add guidance like this to your project instructions:

```markdown
You have access to Atomic, your long-term memory. Search Atomic before answering
questions that may relate to past context. Store durable preferences, decisions,
project context, and important facts. Update stale atoms instead of creating
duplicates.
```

## Troubleshooting

- **Desktop bridge cannot connect** - open Atomic first; the sidecar runs while the desktop app is running.
- **HTTP MCP returns 401** - create a new token and update your MCP client config.
- **Remote OAuth discovery fails** - set `PUBLIC_URL` and verify the `.well-known` routes through your proxy.
- **Agent cannot find expected memory** - check that it is using the intended database.

## Related

- [Token Management](/self-hosting/token-management/)
- [Multi-Database](/guides/multi-database/)
- [Self-Hosting](/getting-started/self-hosting/)
