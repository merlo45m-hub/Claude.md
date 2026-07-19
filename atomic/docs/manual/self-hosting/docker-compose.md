---
title: Docker Compose
description: Deploy Atomic with the server image, web image, nginx proxy, and persistent storage.
---

Docker Compose is the recommended starting point for self-hosting Atomic.

## Basic Setup

Clone the repository and start the included compose file:

```bash
git clone https://github.com/kenforthewin/atomic.git
cd atomic
echo "ATOMIC_SETUP_TOKEN=$(openssl rand -base64 24)" > .env
docker compose up -d
```

Open `http://localhost:8080` and complete first-run setup with the `ATOMIC_SETUP_TOKEN` value from `.env`.

The default compose file starts:

- `server` - `ghcr.io/kenforthewin/atomic-server:latest`
- `web` - `ghcr.io/kenforthewin/atomic-web:latest`
- `proxy` - `nginx:1.28-bookworm`
- `litestream` - optional backup profile

Published image pages:

- [atomic-server](https://github.com/kenforthewin/atomic/pkgs/container/atomic-server)
- [atomic-web](https://github.com/kenforthewin/atomic/pkgs/container/atomic-web)

## Public URL

Set `PUBLIC_URL` when deploying behind a public domain:

```bash
PUBLIC_URL=https://atomic.example.com docker compose up -d
```

`PUBLIC_URL` is used for OAuth/MCP discovery. Without it, OAuth discovery endpoints return 404.

## Reverse Proxy

The included nginx proxy listens on host port `8080`. If you already run Caddy, Traefik, nginx, or another proxy, route traffic to the compose services instead.

Your proxy must support:

- Standard HTTP routes for the web UI and `/api/*`
- WebSocket upgrades for `/ws`
- MCP traffic for `/mcp`
- `/.well-known/*` routes for OAuth/MCP discovery when using remote auth

## Data Persistence

The `atomic-data` volume stores the registry and data databases. Back this volume up to preserve your knowledge base.

```bash
docker volume inspect atomic_atomic-data
```

Volume names are prefixed by the compose project name, so yours may differ.

## Optional Litestream Backup

The compose file includes a `litestream` service under the `backup` profile. Configure these environment variables before enabling it:

- `LITESTREAM_ACCESS_KEY_ID`
- `LITESTREAM_SECRET_ACCESS_KEY`
- `LITESTREAM_BUCKET`
- `LITESTREAM_ENDPOINT`
- `LITESTREAM_PATH`

Then run:

```bash
docker compose --profile backup up -d
```

## Upgrade

```bash
docker compose pull
docker compose up -d
```

Check the server after upgrading:

```bash
curl http://localhost:8080/health
```

## Troubleshooting

- **Web UI loads but API fails** - check proxy routing for `/api/*`.
- **Chat/ingestion progress does not update** - check WebSocket forwarding for `/ws`.
- **MCP remote auth fails** - set `PUBLIC_URL` and confirm `/.well-known/oauth-authorization-server` is reachable.
- **Data disappeared after recreation** - confirm the persistent volume was reused.

## Related

- [First-Run Setup](/self-hosting/first-run-setup/)
- [Configuration](/self-hosting/configuration/)
- [Data and Backups](/self-hosting/data-and-backups/)
