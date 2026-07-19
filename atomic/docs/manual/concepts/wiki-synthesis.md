---
title: Wiki Synthesis
description: Generate cited wiki articles from the atoms under a tag.
---

Wiki articles are AI-synthesized summaries of all atoms under a given tag, with inline citations linking back to source atoms.

## How It Works

1. Atomic gathers atoms tagged with the target tag.
2. Relevant chunks are selected from the available source material.
3. The content is sent to the configured wiki model.
4. The model produces markdown with inline citation markers.
5. Atomic stores the article, citations, and version history.

## Incremental Updates

Wiki articles support incremental updates. When new atoms are tagged:

1. Only the new content is sent to the LLM.
2. The LLM integrates the new information into the existing article.
3. New citations are added for the new sources.

This lets articles evolve as your knowledge base grows without fully regenerating from scratch every time.

## Proposal Flow

Atomic can also generate a proposed wiki update before applying it. The proposal flow lets you inspect an AI-authored update, then accept or dismiss it. This is useful when a tag has important writing you do not want to overwrite automatically.

Relevant API endpoints:

- `POST /api/wiki/{tag_id}/propose`
- `GET /api/wiki/{tag_id}/proposal`
- `POST /api/wiki/{tag_id}/proposal/accept`
- `POST /api/wiki/{tag_id}/proposal/dismiss`

## Citations

Every claim in a wiki article should be backed by an inline citation. Citations link directly to the source atom, so you can verify where information came from.

## Versions and Links

Atomic keeps wiki versions so prior generated content can be inspected later. Wiki articles can also expose cross-reference links to related articles.

Useful endpoints:

- `GET /api/wiki/{tag_id}/versions`
- `GET /api/wiki/versions/{version_id}`
- `GET /api/wiki/{tag_id}/links`
- `GET /api/wiki/{tag_id}/related`
- `POST /api/wiki/recompute-tag-embeddings`

## Troubleshooting

- If a wiki article has too little source material, check that atoms under the tag have completed embeddings.
- If generation fails, verify the configured wiki model and provider key.
- If related tags look missing, recompute tag embeddings.

## Related

- [Tags](/concepts/tags/)
- [AI Providers](/getting-started/ai-providers/)
- [API Overview](/api/overview/)
