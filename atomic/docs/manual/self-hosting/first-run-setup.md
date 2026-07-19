---
title: First-Run Setup
description: Claim a new self-hosted Atomic instance and create the first API token.
---

A fresh self-hosted Atomic instance starts unclaimed when it has no token history. The first user claims it by creating the initial token. First-run setup claims require `ATOMIC_SETUP_TOKEN` unless the server was explicitly started with `--dangerously-skip-setup-token`.

## Setup UI

1. Start the server and web UI.
2. Open the web URL, such as `http://localhost:8080`.
3. Enter `ATOMIC_SETUP_TOKEN` when prompted and follow the setup wizard.
4. Save the displayed API token. It will not be shown again.
5. Configure an AI provider.

The setup wizard connects the browser to the server with the new token and stores the connection in browser local storage.

## Public Setup API

Check whether setup is required:

```bash
curl http://localhost:8080/api/setup/status
```

Response:

```json
{
  "needs_setup": true,
  "already_claimed": false,
  "requires_setup_token": false,
  "setup_token_configured": false
}
```

Claim the instance:

```bash
curl -X POST http://localhost:8080/api/setup/claim \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "setup_token": "'"$ATOMIC_SETUP_TOKEN"'"}'
```

Response:

```json
{
  "id": "token-id",
  "name": "admin",
  "token": "raw-token-shown-once",
  "prefix": "token-pref",
  "created_at": "timestamp"
}
```

After claim, create additional tokens from Settings or `POST /api/auth/tokens`. Setup does not reopen if tokens are revoked; create a replacement token before revoking the old one.

## CLI Alternative

If you are running server-only and do not have the web setup UI available:

```bash
atomic-server --data-dir ./data token create --name admin
```

Use the same `--data-dir`, `ATOMIC_STORAGE`, and `ATOMIC_DATABASE_URL` configuration that your server uses.

## Desktop App Difference

The desktop app does not require claiming a public instance. It creates a local token named `desktop` for the sidecar server and passes that token to the frontend through Tauri IPC.

## Related

- [Self-Hosting](/getting-started/self-hosting/)
- [Token Management](/self-hosting/token-management/)
- [AI Providers](/getting-started/ai-providers/)
