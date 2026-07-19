---
title: Token Management
description: Create, list, and revoke API tokens for server, mobile, browser extension, and MCP access.
---

Atomic server uses named, revocable API tokens stored as SHA-256 hashes. Raw token values are shown only once when created.

## When You Need Tokens

- The desktop app creates and manages its local sidecar token automatically.
- Self-hosted web users need a token after the instance is claimed.
- The iOS app needs a token.
- The browser extension needs a token.
- MCP clients connected over HTTP need a token.
- Scripts and direct API calls need a token.

Use a separate token per device or integration so you can revoke one without disrupting others.

## First Token

Fresh self-hosted instances can be claimed through the setup UI after you configure `ATOMIC_SETUP_TOKEN` and enter that value in the setup wizard:

```bash
export ATOMIC_SETUP_TOKEN="$(openssl rand -base64 24)"
```

The setup endpoints only work before the instance has ever been claimed:

```bash
curl http://localhost:8080/api/setup/status

curl -X POST http://localhost:8080/api/setup/claim \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "setup_token": "'"$ATOMIC_SETUP_TOKEN"'"}'
```

After an instance has been claimed or has any token history, `claim` returns a conflict. Revoking every token does not reopen setup; create a replacement token before revoking an old one.

For trusted development only, `atomic-server serve --dangerously-skip-setup-token` allows first-run setup without `ATOMIC_SETUP_TOKEN`. Do not use it on a server reachable by untrusted clients.

## CLI Commands

For SQLite:

```bash
atomic-server --data-dir ./data token create --name "my-laptop"
atomic-server --data-dir ./data token list
atomic-server --data-dir ./data token revoke <token-id>
```

When running from source:

```bash
cargo run -p atomic-server -- --data-dir ./data token create --name "my-laptop"
```

For Postgres, use the same storage environment variables as the server:

```bash
ATOMIC_STORAGE=postgres \
ATOMIC_DATABASE_URL=postgres://user:pass@host:5432/atomic \
atomic-server token list
```

## API Endpoints

Create token:

```bash
curl -X POST http://localhost:8080/api/auth/tokens \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "new-token"}'
```

List tokens:

```bash
curl http://localhost:8080/api/auth/tokens \
  -H "Authorization: Bearer <admin-token>"
```

Revoke token:

```bash
curl -X DELETE http://localhost:8080/api/auth/tokens/<token-id> \
  -H "Authorization: Bearer <admin-token>"
```

## Usage

Include the token in the `Authorization` header:

```http
Authorization: Bearer <your-token>
```

WebSocket clients pass the token in the query string:

```text
ws://localhost:8080/ws?token=<your-token>
```

## Security Notes

- Save newly created tokens immediately. Atomic stores only a hash and cannot show the raw token again.
- Revoke stale or leaked tokens.
- Prefer HTTPS for remote deployments.
- Use separate tokens for iOS, browser extension, MCP, and scripts.

## Related

- [First-Run Setup](/self-hosting/first-run-setup/)
- [MCP Server](/guides/mcp-server/)
- [Browser Extension](/guides/browser-extension/)
