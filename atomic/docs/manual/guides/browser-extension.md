---
title: Browser Extension
description: Clip web pages and selections into Atomic with the Atomic Web Clipper.
---

The Atomic Web Clipper saves web pages and selected text as atoms. It works with Chromium-based browsers and sends captures to an Atomic server over the same REST API used by the web UI.

## Install

Install the published extension from the [Chrome Web Store](https://chromewebstore.google.com/detail/atomic-web-clipper/bknijbafnefbaklndpglcmlhaglikccf).

For local development, you can also load the repository extension directly:

1. Open Chrome, Edge, Brave, or Arc.
2. Go to `chrome://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select the repository's `extension/` directory.

## Configure

Open the extension settings and enter:

- **Server URL** - for the desktop app, use `http://127.0.0.1:44380`; for self-hosting, use your public server URL.
- **API token** - create a dedicated token in Settings or with the CLI.

For self-hosted servers, the browser must be able to reach the server URL. If the extension runs in your browser on a laptop, `localhost` means the laptop, not your VPS.

## Usage

- **Capture a full page** - right-click the page and choose **Save to Atomic**, or use the extension popup.
- **Capture selected text** - highlight text, right-click, and choose **Save to Atomic**, or use **Capture Selection** from the popup.

The extension extracts article content with Readability, converts it to markdown, includes the source URL, and sends it to Atomic. The atom is then embedded, tagged, and linked by the normal background pipeline.

## Offline Queue

If the server is unreachable, captures are queued locally. The extension retries syncing every 30 seconds and shows the queue count on its badge. You can also trigger a manual sync from the popup.

## Troubleshooting

- **Test Connection fails** - verify the server URL includes `http://` or `https://` and the API token has not been revoked.
- **Desktop app is not reachable** - make sure Atomic is open; the desktop sidecar runs only while the app is running.
- **Self-hosted server is not reachable** - check your reverse proxy and CORS/network access.
- **Duplicate article is skipped** - Atomic may already have an atom with the same source URL.

## Related

- [Token Management](/self-hosting/token-management/)
- [URL Ingestion and Feeds](/guides/url-ingestion-and-feeds/)
- [Self-Hosting](/getting-started/self-hosting/)
