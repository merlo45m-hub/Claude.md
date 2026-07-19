---
title: URL Ingestion and Feeds
description: Save articles by URL and subscribe to RSS or Atom feeds.
---

Atomic can turn web pages into atoms by fetching a URL, extracting readable article content, converting it to markdown, and running the normal embedding/tagging pipeline.

## URL Ingestion

Use `POST /api/ingest/url` to ingest one URL:

```bash
curl -X POST http://localhost:8080/api/ingest/url \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "tag_ids": [],
    "title_hint": null,
    "published_at": null
  }'
```

Successful responses include:

```json
{
  "atom_id": "uuid",
  "url": "https://example.com/article",
  "title": "Article title",
  "content_length": 12345
}
```

Use `POST /api/ingest/urls` for batches. The response groups successful ingestions under `ingested` and failures under `errors`.

## Feeds

Feeds subscribe Atomic to RSS or Atom sources. New entries become atoms and can receive tags automatically.

Create a feed:

```bash
curl -X POST http://localhost:8080/api/feeds \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/feed.xml",
    "poll_interval": 60,
    "tag_ids": []
  }'
```

`poll_interval` is stored in minutes. The default is `60`.

Manage feeds:

```bash
curl http://localhost:8080/api/feeds \
  -H "Authorization: Bearer <token>"

curl -X PUT http://localhost:8080/api/feeds/<feed-id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"poll_interval": 120, "is_paused": false, "tag_ids": []}'

curl -X POST http://localhost:8080/api/feeds/<feed-id>/poll \
  -H "Authorization: Bearer <token>"
```

Poll responses include:

```json
{
  "feed_id": "uuid",
  "new_items": 3,
  "skipped": 10,
  "errors": 0
}
```

## Events

URL and feed workflows emit WebSocket events:

- `ingestion-fetch-started`
- `ingestion-fetch-complete`
- `ingestion-fetch-failed`
- `ingestion-skipped`
- `ingestion-complete`
- `ingestion-failed`
- `feed-poll-complete`
- `feed-poll-failed`

## Desktop vs Self-Hosted

The desktop app can ingest URLs through its local sidecar while Atomic is open. Feeds are more useful on a self-hosted server because the server needs to keep running to poll on schedule.

If the server is behind a proxy, it must be able to make outbound HTTP requests to the feed and article URLs.

## Troubleshooting

- **No new items** - the feed entries may already exist by source URL.
- **Fetch failed** - verify the server can reach the URL and the site does not block server-side fetches.
- **Content is thin** - the article may not expose readable content to extraction.
- **Embeddings not complete** - check `/api/embeddings/status` after ingestion.

## Related

- [Browser Extension](/guides/browser-extension/)
- [Importing Data](/guides/importing-data/)
- [Atoms](/concepts/atoms/)
