# LLM Wiki Gist — Ideas to Incorporate into Atomic

Analysis of Karpathy's trending gist ([llm-wiki.md](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md)) and what it suggests for Atomic.

## Overlap with what Atomic already does

The gist describes a pattern where an LLM incrementally builds and maintains a persistent wiki as an alternative to re-synthesizing from raw documents on every query. Atomic already implements most of this substrate:

- Per-tag wiki articles with citations and incremental updates
- Auto-tagging into entity categories (Topics, People, Locations, Organizations, Events)
- Semantic edges between atoms
- Tag tree as organizational scaffolding
- Canvas as a graph view
- Tag-scoped agentic RAG chat

The gist's core framing — wiki as compounding artifact where "the cross-references are already there, the contradictions have already been flagged" — is the pitch Atomic is already built around.

## Ideas worth incorporating

Ranked by impact.

### 1. Lint pass (biggest gap, biggest differentiator)

Karpathy's third operation — a periodic agent that hunts for contradictions between sources, stale claims, orphan pages (no edges/tags), and missing cross-references. Atomic has all the substrate for this (chunks, embeddings, edges, tags) but no agent that actively audits the graph. A "Lint" panel showing "these two atoms disagree about X" or "these 12 atoms have no semantic neighbors" would be a killer feature and plays directly to the knowledge-base-as-living-thing pitch.

Concretely: a new background job + `lint_reports` table, surfaced as a dashboard view. Contradiction detection could be a specialized semantic edge type (`conflicts_with`) alongside the existing similarity edges.

### 2. Aggressive ingest — revise, don't just append

Right now when an atom is saved, the pipeline chunks/embeds/tags/edges and (if tagged) incrementally updates wiki articles. Karpathy's framing: a single new source should "touch 10-15 pages" — the LLM actively reconciles new info against existing entity pages, flags contradictions, updates related atoms' wiki entries. Atomic does the wiki update but not the cross-atom reconciliation.

Could extend the pipeline to run a "reconcile" step after tagging that diffs new content against neighboring atoms in embedding space and proposes edits/flags.

### 3. Activity log / timeline

`log.md` in the gist — append-only record of ingests, queries, lint passes. Atomic has no activity surface at all. Users have no visibility into what the pipeline has been doing in the background. A simple timeline view ("12 atoms ingested, 3 wiki articles updated, 2 contradictions flagged today") would make the async pipeline legible and is cheap to build on top of the existing event system.

### 4. Promote chat answer → atom

Gist: "good answers can be filed back into the wiki as new pages." Right now Atomic's chat is a dead end — answers stream, user reads, gone. A one-click "save this answer as an atom" (with the cited source atoms automatically becoming semantic edges) closes the loop and turns chat from query tool into a knowledge-creation surface.

### 5. Schema layer per database

Karpathy's `CLAUDE.md`/`AGENTS.md` idea — user-editable conventions for how the LLM maintains the wiki, varying by domain (book notes vs research vs journal). Atomic has global provider settings but no per-database prompt/convention customization. A `schema.md` stored per database that gets injected into tagging, wiki synthesis, and chat system prompts would let people tune Atomic to very different use cases without code changes.

### 6. Entity pages as first-class (UI framing)

Atomic already has this under the hood — auto-tags go under People/Locations/Organizations/Events parents, and each tag can have a wiki article. But the UI frames them as "tags with filters," not "entity pages." A richer rendered view for entity-type tags (infobox, mentions, timeline of atoms referencing them) would make this visible. Pure UI work, no backend changes.

## Ideas to skip

- **Raw-sources-vs-wiki separation.** Atomic's "atom = unit of thought" model is cleaner than a two-layer split, and changing it would be a huge architectural cost for minimal gain.
- **Marp/slides/charts output modes.** Cute but not core to the value prop.

## Recommended first bet

**Lint.** It's the most novel relative to what's shipping today, it showcases the semantic graph already built, and it reframes Atomic from "notes + search" to "notes that maintain themselves" — which is exactly the positioning the gist is making trend.
