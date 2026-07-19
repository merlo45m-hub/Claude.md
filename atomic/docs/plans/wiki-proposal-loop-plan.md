# Plan: Human-in-the-loop Background Wiki Updates

## Scope

Build a background process that pre-computes wiki article updates as **proposals** — the user reviews a diff and explicitly accepts before anything changes in the live article. One pending proposal per article, always superseded from the live baseline, debounced by a dirty set.

Explicitly **out of scope for v1**:

- Edits and deletes (only insert-driven staleness)
- Rejection tracking (user rejection just means "not yet"; loop will re-propose with more atoms later)
- Atom-level coverage tracking (we accept that centroid-ranked chunk selection may drop atoms on bursty ingests)
- A unified inbox surface for lint + proposals (defer until lint lands)
- Auto-apply / graduated trust per article

## Architecture Decisions

- **Supersede, never chain.** At most one pending proposal per article, always built from the live accepted version plus atoms since its `updated_at`. New atom arrives while a proposal is pending → throw the old proposal away, regenerate.
- **Debounced trigger.** Atom tag events push tag IDs into an in-memory dirty set. A tokio interval drains the set periodically and regenerates one proposal per dirty tag.
- **Lock during review.** While a user has a proposal open in the UI, skip regeneration for that article until they close the drawer.
- **Per-tag mutex** around `update_wiki()` to prevent concurrent background + manual runs from racing.
- **Loop lives in `atomic-server/src/main.rs`**, following the RSS feed poller pattern. Tauri inherits it via the sidecar. Core stays framework-free.
- **Opt-in, default off.** New setting `wiki_auto_propose_enabled`. Don't surprise users with background LLM calls until they ask for it.
- **Section-scoped updates, not full rewrites.** The LLM emits a list of structured section operations against the existing article (append / replace / insert / no_change); an applier merges them into the final content. Untouched sections stay byte-identical, which makes the review diff naturally localized, preserves the existing citation graph, and cuts output tokens proportional to scope of change. Only the update path changes — first-time generation stays full-article. See M1 for details.

## Cost & Runaway Protection

Non-negotiable guardrails. A batch import or RSS poll can create hundreds of atoms across many tags in a short window; without these, supersede-based regeneration turns that into compounding LLM spend. All of these land in M2 — none are "polish."

1. **Quiet-window, not fixed debounce.** Propose only when a tag has been dirty *and* has seen no new atoms for `QUIET_WINDOW` (default 10 min). Any new atom resets the timer. A 500-atom burst collapses to exactly one proposal per affected tag, regardless of burst length.
2. **Per-tag cooldown.** After a proposal is created (accepted, dismissed, or superseded), lock the tag out of re-proposing for `COOLDOWN` (default 30 min). Prevents ping-pong when atoms trickle in just past the quiet window.
3. **Supersede budget per tag.** If a pending proposal has been superseded `MAX_SUPERSEDES` times (default 3) without user review, stop regenerating and wait. The user isn't keeping up; burning more tokens won't help. Resets when the user accepts or dismisses.
4. **Daily proposal caps.** Hard limits on proposal *count* (not token budgets — too granular for v1):
   - Max proposals per database per day (default 20)
   - Max proposals per tag per day (default 3)
   - When hit, dirty tags stay dirty and drain on the next window. No lost work, just delayed.
5. **Provider-reachable precheck.** Skip the loop iteration entirely if the configured LLM provider is unreachable. Don't drain the dirty set into failures.
6. **Counters from day one.** `proposals_created`, `superseded`, `accepted`, `dismissed`, `skipped_cooldown`, `skipped_budget`, `skipped_provider_down`. Exposed via an admin route or dev panel. You want to watch these during the first weeks with real data — adding them later means flying blind through the riskiest window. Token-cost estimation is deferred.

Note on the "min 2 atoms" threshold: keep it as a noise filter, but don't let it carry burst-protection weight. Quiet-window + cooldown do that job.

## Milestones

Three vertical slices, each independently shippable and testable.

### Milestone 1 — Proposal as a Data Model (Manual Trigger)

Ship the proposal flow end-to-end using the *existing* user click. The "Update Article" button writes to a proposal, not to the live article; user sees a diff view and clicks "Accept" to promote. This gets the review UX working before we add any scheduler.

**Schema.** New table:

```sql
CREATE TABLE wiki_proposals (
    id TEXT PRIMARY KEY,
    tag_id TEXT UNIQUE NOT NULL,           -- one pending proposal per article
    base_version_id TEXT NOT NULL,          -- live article this was computed from
    content TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    new_atom_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
```

Separate from `wiki_article_versions` — proposals are transient and overwritten, versions are permanent history. On accept, the proposal row is deleted and a new row is written to `wiki_article_versions` + `wiki_articles` via the existing accepted-update path.

**Generation model: section operations.**

The current update path (`wiki/mod.rs:86` `strategy_update` → `wiki/mod.rs:141` `call_llm_for_wiki` with `WIKI_UPDATE_SYSTEM_PROMPT`) asks the LLM to produce a full rewritten article and returns it via the existing `WikiGenerationResult { article_content, citations_used }` schema. We swap this for a structured-ops approach, reusing the same LLM call infrastructure with a different schema and prompt.

New result type and schema passed to `call_llm_for_wiki` on the update path:

```rust
#[derive(Deserialize)]
pub(crate) enum WikiSectionOp {
    NoChange,
    AppendToSection  { heading: String, content: String },
    ReplaceSection   { heading: String, content: String },
    InsertSection    { after_heading: Option<String>, heading: String, content: String },
}

#[derive(Deserialize)]
pub(crate) struct WikiUpdateResult {
    pub operations: Vec<WikiSectionOp>,
    pub citations_used: Vec<i32>,
}
```

- Heading match is by exact `##`/`###` text against the existing article. Applier errors out (and the proposal is discarded) if a referenced heading doesn't exist — that's a model hallucination, not something to paper over.
- `after_heading: None` on `InsertSection` means "append as a new top-level section at the end."
- If the model returns `[NoChange]` or an empty operations list, `strategy_update` returns `Ok(None)` — same no-op semantics the current code already has.
- An empty operations list + `content` containing only the same material already in the article is *not* something we try to detect. If the model says "no change," we trust it.

New applier `apply_section_ops(existing: &str, ops: &[WikiSectionOp]) -> Result<String, String>`:

- Parses the existing article's section headers (same `##` / `###` structure the generation prompt already emits).
- Applies each op in order against the section boundaries.
- Returns the merged article text. Untouched sections are spliced through byte-for-byte.
- Lives in `wiki/section_ops.rs` as a pure function — easy to unit test with fixture articles and op lists.

Citations flow unchanged: the LLM's new-content strings contain `[N]` markers using the next-available numbering (the prompt provides the current max citation index). After the applier merges everything, `extract_citations` (`wiki/mod.rs:247`) runs over the final article exactly as it does today.

New system prompt `WIKI_UPDATE_SECTION_OPS_PROMPT`, replacing `WIKI_UPDATE_SYSTEM_PROMPT` on the update path. Guidelines: emit operations only for sections that genuinely need to change; prefer `AppendToSection` over `ReplaceSection` when adding material; use `InsertSection` sparingly and only for genuinely new topics; return `[NoChange]` if the new atoms don't warrant an update; continue citation numbering from the provided max.

Both `centroid::update` and `agentic::update` switch to this flow. First-time `generate` paths are untouched.

**Core changes.**

- `AtomicCore::propose_wiki_update(tag_id)` — runs the update strategy (now section-ops), applies the ops to the live article, writes the merged content + citations to `wiki_proposals` instead of mutating `wiki_articles`. Supersedes any existing proposal for that tag. Returns `None` if the strategy returns no-op.
- `AtomicCore::accept_wiki_proposal(tag_id)` — promotes the pending proposal to live (calls the existing save-wiki-version path, deletes the proposal row).
- `AtomicCore::dismiss_wiki_proposal(tag_id)` — deletes the proposal without promoting.
- `AtomicCore::get_wiki_proposal(tag_id)` — read.
- Storage trait methods for all of the above in both sqlite and postgres backends.
- Per-tag mutex (a `DashMap<TagId, Arc<Mutex<()>>>` inside `AtomicCore`) wrapping the propose/accept paths.

**Server routes.**

- `POST /api/wiki/{tag_id}/propose` (replaces the semantic of the old `/update` — see rewire below)
- `POST /api/wiki/{tag_id}/proposal/accept`
- `POST /api/wiki/{tag_id}/proposal/dismiss`
- `GET /api/wiki/{tag_id}/proposal`

**Rewire the existing "Update Article" button.** Today it calls `/update` which directly mutates. In M1 it calls `/propose` instead. After proposal is created, the banner UI changes from "N new atoms available" to "suggested update ready — review" and clicking opens the diff view.

**Frontend.**

- New store methods in `src/stores/wiki.ts`: `proposeArticle`, `acceptProposal`, `dismissProposal`, `fetchProposal`.
- New command map entries in `src/lib/transport/command-map.ts` for the four routes.
- Update `WikiHeader.tsx:168-192` banner: when `newAtomsAvailable > 0` and no proposal exists, show "N new atoms available — generate update" (calls propose). When a proposal exists, show "suggested update ready — review" which opens the diff view.
- New `WikiProposalDiff.tsx` component: side-by-side or unified diff of `liveArticle.content` vs `proposal.content`, with Accept / Dismiss buttons. Citation markers render as links. Uses an existing diff library if one is in the dep tree, otherwise a small hand-rolled line diff is fine for v1 since the LLM keeps most sentences stable.
- Add proposal state to the wiki store so the diff view can be opened from the banner without extra fetches.

**Keep `/update` for backwards compat** temporarily — flag it deprecated but leave it working so external MCP clients don't break. Remove in a later release.

**Exit criteria for M1.** A user clicks "generate update" on an existing wiki, sees a localized diff showing only the sections the LLM chose to modify (untouched sections byte-identical), clicks accept or dismiss, and the live article either changes or doesn't. Unit tests cover the section applier with append / replace / insert / no-change fixtures and with a hallucinated-heading error case. No scheduler yet. No UI changes outside the wiki viewer.

### Milestone 2 — Background Scheduler

Now that proposals exist as a data model and the review UX works, add the loop that creates proposals automatically.

**Dirty set.** Add `wiki_dirty_tags: Arc<Mutex<HashSet<(DbId, TagId)>>>` to `AtomicCore` (or a dedicated component owned by the server). Hook:

- After `atom_tags` inserts in the atom create/update/tag paths, insert all affected tag IDs into the set.
- Consider ancestor tags too: if an article exists for a parent tag, inserting an atom under a child should also mark the parent dirty (tag hierarchies roll up via the existing recursive CTE used by `get_wiki_status`). Walk up the tree once per insert.

**Lock-during-review signal.** Add `wiki_locked_tags: Arc<Mutex<HashSet<TagId>>>`. New server routes `POST /api/wiki/{tag_id}/lock` and `/unlock` called from the frontend when the proposal diff view opens and closes. The loop skips any tag currently locked.

**The loop.** In `atomic-server/src/main.rs`, alongside the feed poller:

```rust
tokio::spawn(async move {
    let mut ticker = tokio::time::interval(Duration::from_secs(60));
    loop {
        ticker.tick().await;
        if !settings.wiki_auto_propose_enabled { continue; }
        if !core.provider_reachable().await { continue; } // skip tick if LLM down
        for db in registry.list_databases() {
            let core = get_core_for_db(&db);
            if core.daily_db_cap_reached() { continue; }
            let dirty = core.drain_dirty_tags_ready(); // quiet-window + cooldown + caps
            for tag_id in dirty {
                if core.is_tag_locked(&tag_id) { continue; }
                // per-tag mutex inside propose_wiki_update handles concurrent-manual races
                if let Err(e) = core.propose_wiki_update(&tag_id).await {
                    tracing::warn!(?tag_id, ?e, "background propose failed");
                }
            }
        }
    }
});
```

**Quiet-window logic inside `drain_dirty_tags_ready`.**

- Track `last_marked_at` per tag. Every new atom for that tag updates it.
- Only drain tags where `now - last_marked_at > QUIET_WINDOW` (default 10 min). Tags still receiving atoms keep resetting and stay in the set.
- Also require `new_atoms_available >= 2` as a noise filter (not a burst guard — quiet-window handles bursts).
- Respect the per-tag cooldown, supersede budget, and daily caps from the Cost & Runaway Protection section before proposing.
- All thresholds configurable via settings with sensible defaults.

**Multi-database iteration.** Check what the RSS poller does in `main.rs:265` — if it already walks the registry, copy the pattern. If it's single-db, this milestone also generalizes the pattern (small refactor).

**Events.** New `ServerEvent` variants broadcast on the channel:

- `WikiProposalCreated { db_id, tag_id }`
- `WikiProposalSuperseded { db_id, tag_id }`
- `WikiProposalAccepted { db_id, tag_id }`
- `WikiProposalDismissed { db_id, tag_id }`

Frontend subscribes via `transport.subscribe('wiki-proposal-*', ...)` and updates local state. The wiki store gains a `pendingProposals: Record<TagId, ProposalMeta>` map that events keep in sync.

**Tag tree badge.** Small dot (or count) next to any tag in the left panel tag tree whose ID is in `pendingProposals`. Click the tag → filter to it as usual, user can open the wiki viewer from there and see the existing "review" banner. That's the whole discovery surface for v1 — no separate inbox view.

**Settings UI.** A single toggle in the settings panel: "Automatically propose wiki updates in the background." Default off. When toggled on for the first time, optionally show a one-liner explaining what it does and that proposals require explicit acceptance.

**Exit criteria for M2.** With the setting enabled, adding atoms under a tagged article causes a proposal to appear within ~10 minutes of the last atom in the burst, without any user action. A simulated 500-atom import across 10 tags produces at most 10 proposals, not hundreds. Per-tag cooldown, supersede budget, and daily caps are enforced and counted. The tag tree shows a badge. Opening the wiki viewer shows the review banner. Accepting or dismissing works. Concurrent manual clicks on "generate update" don't race. Counters are queryable.

### Milestone 3 — Polish

Small things that make it feel good but don't block shipping. (Guardrails and counters live in M2 — they're prerequisites, not polish.)

- **Proposal age display** in the diff view: "computed 14 min ago, based on 3 new atoms."
- **"Regenerate this proposal"** button in the diff view, in case the user wants a fresh take on the same input (rare, but useful for debugging prompt quality).
- **Nicer surfacing for cap/cooldown state.** If a tag is currently blocked by cooldown or daily cap, the wiki header can say so ("next auto-update available in 22 min") instead of silently doing nothing.
- **Tuning pass** on `QUIET_WINDOW`, `COOLDOWN`, `MAX_SUPERSEDES`, and daily caps based on real usage from M2 counters.

## Known Gaps We're Shipping With

Worth writing down so they don't get lost:

1. **Centroid-ranked chunk selection can drop atoms.** An atom arrives, its chunks get outranked by more on-topic material from other new atoms, it's never reflected in the wiki, and because its `created_at` is older than the next `updated_at` it won't retrigger. The tracking table (`wiki_article_sources`) fixes this but is deferred. Watch for it in practice.
2. **Edits and deletes don't mark stale.** If an atom is rewritten or removed, the article won't propose an update. Manual "Regenerate" from scratch is the escape hatch.
3. **Tag hierarchy rollup on dirty marking** walks ancestors at tag time. If tag hierarchies are deep or atoms are retagged frequently this could get chatty. Simple to measure and bound if it becomes an issue.
4. **No unified inbox surface yet.** Tag tree badges are the only discovery mechanism. Fine for a small number of articles; worth revisiting when lint ships and wants the same real estate.
5. **One in-memory dirty set per server process.** If the server restarts, pending dirtiness is lost. Acceptable because the next atom save will re-dirty the relevant tags, and the loop is idempotent. Don't persist to the DB unless telemetry shows restarts are common enough to matter.

## Open Tuning Questions

Both small, both can be revisited after v1 ships:

1. **Default debounce window.** Proposed: 10 minutes. Long enough to collapse a writing session, short enough to feel responsive.
2. **Minimum atom threshold before proposing.** Proposed: 2. Avoids single-atom noise without being so high it delays obvious updates.
