---
title: Self-Hosting
description: Run Atomic as a headless server for remote access, mobile clients, and integrations.
---

Atomic can run as a self-hosted server for remote access, web UI usage, mobile clients, browser clipping, and MCP over HTTP. This is the right mode when Atomic needs to be reachable from devices other than the desktop app.

## What Gets Hosted

A production self-hosted setup usually has:

- `atomic-server` - REST API, WebSocket events, MCP endpoint, scheduled jobs, and database access
- `atomic-web` - the browser UI
- A reverse proxy - nginx, Caddy, Traefik, or another proxy that routes HTTP and WebSocket traffic
- Persistent storage - a volume or directory for `registry.db`, data databases, and temporary export artifacts

## Quick Start with Docker Compose

```bash
git clone https://github.com/kenforthewin/atomic.git
cd atomic
echo "ATOMIC_SETUP_TOKEN=$(openssl rand -base64 24)" > .env
docker compose up -d
```

The default compose file starts:

- `ghcr.io/kenforthewin/atomic-server:latest`
- `ghcr.io/kenforthewin/atomic-web:latest`
- `nginx:1.28-bookworm` as a local proxy on `http://localhost:8080`

Open `http://localhost:8080` and claim the instance in the setup wizard with the `ATOMIC_SETUP_TOKEN` value from `.env`. The server and web images are published through GitHub Container Registry:

- [atomic-server package](https://github.com/kenforthewin/atomic/pkgs/container/atomic-server)
- [atomic-web package](https://github.com/kenforthewin/atomic/pkgs/container/atomic-web)

## Server-Only Container

If you only need the API server and will provide your own frontend or reverse proxy, you can run just the server image:

```bash
docker run -d \
  --name atomic-server \
  -p 8080:8080 \
  -v atomic-data:/data \
  -e PUBLIC_URL=https://atomic.example.com \
  -e ATOMIC_SETUP_TOKEN="$(openssl rand -base64 24)" \
  ghcr.io/kenforthewin/atomic-server:latest
```

The server image stores data under `/data`. Set `PUBLIC_URL` when using remote MCP OAuth discovery or clients that need your externally reachable URL.

## From Source

```bash
git clone https://github.com/kenforthewin/atomic.git
cd atomic
cargo run -p atomic-server -- --data-dir ./data serve --bind 0.0.0.0 --port 8080
```

Open `http://localhost:8080/health` to verify the server is running. The API docs are available at `/api/docs` and `/api/docs/openapi.json`.
Set `ATOMIC_SETUP_TOKEN` and enter that value in the setup wizard for the first claim, or create the first API token with the CLI.

## Authentication

Self-hosted Atomic uses Bearer token authentication. The web setup wizard can claim a fresh instance by creating the first token after you enter `ATOMIC_SETUP_TOKEN`. You can also create tokens from the CLI:

```bash
cargo run -p atomic-server -- --data-dir ./data token create --name "my-laptop"
cargo run -p atomic-server -- --data-dir ./data token list
cargo run -p atomic-server -- --data-dir ./data token revoke <token-id>
```

See [Token Management](/self-hosting/token-management/) for more details.

## Reverse Proxy Requirements

If you put Atomic behind your own proxy, make sure it forwards:

- HTTP requests for the web UI and `/api/*`
- WebSocket upgrades for `/ws`
- MCP traffic for `/mcp`
- OAuth discovery paths under `/.well-known/` when using remote MCP auth

Set `PUBLIC_URL=https://your-domain.example` when the server should advertise a public URL for OAuth/MCP discovery.

## Next Steps

- [First-run setup](/self-hosting/first-run-setup/)
- [Docker Compose setup](/self-hosting/docker-compose/)
- [Configuration options](/self-hosting/configuration/)
- [Connect the iOS app](/guides/ios-app/)
- [Configure MCP](/guides/mcp-server/)
