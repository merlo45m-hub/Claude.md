---
title: Semantic Search
description: Search your knowledge base by meaning using vector embeddings and hybrid retrieval.
---

Semantic search finds atoms by meaning rather than exact wording. It works best after embeddings have completed for the atoms you want to search.

## How It Works

1. Your query is converted to a vector embedding using the configured embedding model.
2. The query vector is compared against atom chunk embeddings.
3. Results are ranked by similarity and returned with the matching chunk.

Atomic computes similarity from sqlite-vec's Euclidean distance on normalized vectors:

```text
similarity = 1.0 - (distance^2 / 2.0)
```

## Search Modes

Atomic supports multiple search modes:

- **Keyword** - Full-text search over atom content, wiki articles, chat messages, and tags depending on the endpoint.
- **Semantic** - Pure vector similarity search.
- **Hybrid** - Combines semantic search with full-text keyword matching.

The main search endpoint is `POST /api/search` with `mode` set to `keyword`, `semantic`, or `hybrid`. The global search endpoint, `POST /api/search/global`, is keyword-based and groups results across atoms, wiki articles, chats, and tags.

## Thresholds

Default thresholds:

- **0.5** - Related atoms and semantic edge creation.
- **0.3** - Search results and wiki chunk selection.
- **0.7** - Default threshold for `GET /api/atoms/{id}/similar`.

## When Search Looks Wrong

- If semantic or hybrid search returns stale results, check `/api/embeddings/status`.
- If only keyword search works, the AI provider may not be configured or embeddings may have failed.
- If you changed embedding models, re-embed all atoms before comparing results.
- If you are self-hosting multiple databases, confirm you are searching the intended active database or pass `?db=<database-id>` / `X-Atomic-Database`.

## Related

- [AI Providers](/getting-started/ai-providers/)
- [Atoms](/concepts/atoms/)
- [API Overview](/api/overview/)
