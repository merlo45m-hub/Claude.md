---
title: iOS App
description: Connect Atomic KB on iPhone or iPad to a self-hosted Atomic server.
---

The native iOS app is called [Atomic KB on the App Store](https://apps.apple.com/us/app/atomic-kb/id6759266634). It is a thin client for a self-hosted Atomic server, not a standalone local database.

## Requirements

- iOS 17 or later
- A running self-hosted `atomic-server` reachable from your device
- An API token
- HTTPS for most real-world remote deployments

The App Store listing describes iPhone and iPad support. The app connects to your own server for browsing, creating, editing, searching, and sharing content into Atomic.

## Connect with QR Code

The Atomic web and desktop onboarding flows can generate a QR code containing a server URL and a new API token.

1. Open Atomic on the server or desktop that can create tokens.
2. Go to the mobile setup step or integration settings.
3. Generate a mobile token.
4. Open Atomic KB on iOS.
5. Scan the QR code.

## Connect Manually

You can also enter:

- Server URL, such as `https://atomic.example.com`
- API token
- Optional database selection after connection

The iOS client sends the selected database with the `X-Atomic-Database` header when a database is selected.

## Features

- Browse atoms
- Create and edit markdown atoms
- Delete atoms
- Browse tags and tag children
- Filter by tag and source
- Hybrid, semantic, and keyword search
- Switch databases on a multi-database server
- Queue new atoms while offline and sync them later
- Save URLs from Safari or other apps through the iOS Share Extension

The Share Extension sends shared URLs to `POST /api/ingest/url`, so the server fetches and extracts the article before creating the atom.

## Self-Hosted Server Notes

The iOS app is designed for self-hosted server access. If you are using only the desktop app, the local sidecar at `127.0.0.1:44380` is not reachable from your phone unless you expose it on your network and handle tokens deliberately. For mobile use, run a self-hosted server or connect the app to a server reachable from the phone.

## Troubleshooting

- **Cannot connect** - open the server URL from Safari on the same device and verify it loads.
- **401 or reconnect loop** - create a new API token and update the app.
- **Share Extension says not configured** - open the main iOS app and connect to a server first.
- **Search is empty** - check that embeddings are complete on the server.

## Related

- [Self-Hosting](/getting-started/self-hosting/)
- [Token Management](/self-hosting/token-management/)
- [Multi-Database](/guides/multi-database/)
