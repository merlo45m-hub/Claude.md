# URL Ingestion Improvements — Lessons from Obsidian Web Clipper

Atomic's current URL-to-atom pipeline (`crates/atomic-core/src/ingest/extract.rs`) is a single-shot call to `dom_smoothie::Readability::parse()` in Markdown mode. Clean, but it leaves a lot on the table. Obsidian Clipper delegates everything to **Defuddle** (kepano's Readability+Turndown replacement), which does several things `dom_smoothie` doesn't.

This doc captures concrete recommendations for closing the gap.

## High-value, low-effort wins

### 1. Stop discarding extracted metadata
`extract.rs:37-39` pulls `byline`, `excerpt`, `site_name`, but only `title` and `content` reach `Atom`. The schema already has `source`, `published_at`, `snippet` — wire `byline`/`excerpt`/`site_name` into new or existing columns. Defuddle goes much further with deep fallback chains across OG, Twitter Card, Dublin Core, Sailthru, `citation_*`, JSON-LD, and microdata — worth porting the priority list even without Defuddle itself.

### 2. Published-date auto-extraction
Today `published_at` must be passed in by the caller (`routes/ingest.rs:29-49`). Every clipper client currently omits it. Add a metadata-extraction pass:

- JSON-LD `datePublished`
- `<time>` elements
- OG `article:published_time`
- `citation_publication_date`

### 3. Schema.org length cross-check
Defuddle's most clever self-correction: if the extracted body is <1.5× shorter than JSON-LD `articleBody`, re-select a container matching that text. Cheap sanity check that catches cases where Readability clips too aggressively. Worth adding as a post-pass over `dom_smoothie` output.

## Architectural shifts worth considering

### 4. Replace `dom_smoothie` with Defuddle, or layer Defuddle-style passes on top
Defuddle is JS/TS, so direct reuse means either:

- (a) shelling out to a Node sidecar
- (b) porting the passes to Rust
- (c) running it client-side in the browser/iOS clippers and sending pre-extracted markdown

Option (c) is probably the right call — the `extension/` already bundles Readability+Turndown (~117KB); swapping for Defuddle gives you everything below for free on the client side, and the server path stays as a fallback for headless callers (iOS share extension, MCP, API).

### 5. Mobile-CSS clutter reveal
Defuddle's most novel trick: parse `@media (max-width:…)` rules and apply them inline before extraction, letting the *site itself* tell you what's clutter. Radically better than heuristic link-density scoring for modern sites.

### 6. Progressive filter relaxation
If extraction yields <50 words, retry with relaxed filters (scoring → partial selectors → allow hidden). `dom_smoothie` is single-pass; Atomic's 200-char gate in `extract.rs` currently just fails.

### 7. Site-specific extractor registry
Defuddle/Clipper ships 16 ordered `(pattern, Extractor)` pairs with shared base classes — notably a `_conversation.ts` base for Claude/ChatGPT/Gemini/Grok transcripts as a first-class content type. For Atomic, where the user is already clipping AI conversations into a knowledge base, this is especially relevant: a plain-Readability pass on a ChatGPT share link produces garbage. A small extractor registry in `ingest/extract.rs` keyed on host would be a big quality jump with modest code. YouTube (transcript), GitHub (README + file), Reddit, Substack, X are the other obvious targets.

### 8. Special-content normalization
Defuddle standardizes:

- **Math**: MathML/KaTeX → `$$`
- **Footnotes**: `[^id]` with backlinks
- **Callouts**: GitHub alerts, Obsidian callouts, Bootstrap → `> [!type]`
- **Code blocks**: language detection across `data-lang`/`data-language`/class
- **Images**: `srcset` width-descriptor preference

Each is small; together they're the difference between "readable clip" and "looks like the original."

## Prioritized recommendation

If you want the best ROI sequence:

1. **Wire existing Readability metadata into the atom** (byline/excerpt/site_name) — hours of work, already extracted, currently thrown away. `extract.rs:37` + `models.rs:11` + a migration.
2. **Add a metadata pass** for JSON-LD / OG / `<time>` so `published_at` and `source` get populated automatically across all clippers. This fixes all four clients at once because they all hit `POST /api/ingest/url`.
3. **Site-specific extractor registry** starting with AI chat transcripts (Claude/ChatGPT share URLs) and YouTube. This is where generic Readability fails hardest and where Atomic's target user clips most.
4. **Switch client-side extractors to Defuddle** in `extension/` and plan a Defuddle-equivalent for iOS share extension. Keep `dom_smoothie` server-side as fallback.
5. **Port the two highest-leverage Defuddle tricks to the Rust path**: schema.org length cross-check and progressive retry. Skip the mobile-CSS trick server-side (hard in Rust) — it's really a client-DOM technique.

## Key references

**Atomic**
- `crates/atomic-core/src/ingest/extract.rs:7-39`
- `crates/atomic-core/src/models.rs:11-23`
- `crates/atomic-server/src/routes/ingest.rs:29-49`
- `extension/readability.min.js`

**Obsidian side**
- `kepano/defuddle` — `src/defuddle.ts`, `src/standardize.ts`, `src/metadata.ts`
- `obsidianmd/obsidian-clipper` — `src/extractor-registry.ts`, `src/extractors/_conversation.ts`
