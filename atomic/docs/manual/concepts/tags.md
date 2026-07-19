---
title: Tags
description: Hierarchical tags organize atoms and scope wiki generation, chat, canvas views, imports, and feeds.
---

Tags form a hierarchical tree that organizes your atoms. They are both an organization tool and a scoping mechanism for other features.

## Hierarchy

Auto-extracted tags are organized under category parents:

- **Topics** - Subject matter, such as `Topics/Machine Learning`.
- **People** - Named individuals mentioned in your notes.
- **Locations** - Places referenced in your content.
- **Organizations** - Companies, institutions, and groups.
- **Events** - Named events, conferences, and incidents.

You can also create your own parent tags and assign atoms manually.

## Auto-Tagging

When auto-tagging is enabled, Atomic's LLM pipeline analyzes new or updated atom content and extracts relevant tags using structured outputs.

Auto-tagging can be disabled with the `auto_tagging_enabled` setting. Atomic also tracks which top-level tags are auto-tag targets, so you can preserve the default taxonomy while adding custom target branches.

## Manual Tags

Manual tags coexist with auto-extracted tags. You can attach them in the editor, during API creation with `tag_ids`, or through import/ingestion/feed workflows.

Deleting tags can be non-recursive or recursive depending on the API/UI action.

## Tags as Scope

Tags define scope for:

- **Wiki articles** - Synthesize all atoms under a tag.
- **Chat conversations** - Restrict retrieval to selected tags.
- **Canvas views** - Focus the graph on a subtopic.
- **Imports and ingestion** - Assign tags as content enters Atomic.
- **Feeds** - Apply tags to every new item from a feed.

## Related Tags

Atomic computes tag embeddings and semantic connectivity so wiki pages can surface related tags. If related tags look stale after major imports or model changes, recompute tag embeddings from the wiki tools or call:

```bash
curl -X POST http://localhost:8080/api/wiki/recompute-tag-embeddings \
  -H "Authorization: Bearer <token>"
```

## Related

- [Wiki Synthesis](/concepts/wiki-synthesis/)
- [Chat](/concepts/chat/)
- [URL Ingestion and Feeds](/guides/url-ingestion-and-feeds/)
