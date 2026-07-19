# Reports — Automated Research as a First-Class Primitive

## Context

Atomic's daily briefing — the most-used surface for the maintainer — is a
specific instance of a more general pattern: take a *scope of atoms* (recent
ones, under a tag, in a time window), run an agentic LLM loop with
`semantic_search` and `read_atom`, produce a synthesized prose artifact that
cites the atoms it drew on. The briefing hardcodes one shape of that pattern;
every other useful shape ("what new tensions appeared in my AI-safety reading
this week," "what open questions got answered," "what themes are emerging in
my policy notes") would today require its own bespoke code path.

This plan promotes the pattern to a first-class primitive — a **Report** —
parallel to the existing **Wiki** primitive. The briefing becomes the first
default report on every database. Users define additional reports with their
own scopes, prompts, and schedules. Each report run produces a single
**finding atom** that enters the knowledge graph on equal footing with any
captured note.

## Goals

- A per-DB `reports` table: research definitions (scope, prompt, schedule).
- A report run produces exactly **one finding atom** per run, cited back to
  the atoms it consulted, tagged predictably so it is discoverable.
- The atoms table gains a `kind` discriminator (`captured` | `report`) and
  every context-assembly code path filters on it with safe defaults.
- Report findings have durable provenance back to the report definition that
  produced them; run-history retention must never be the only link.
- The daily briefing collapses into a seeded default report; the hardcoded
  briefing execution path is removed.
- Reports are database-scoped. Each database seeds its own default report on
  creation; the database's dashboard featured-report slot is configurable.
- SQLite and Postgres both ship in scope. The tables are per data database in
  SQLite and `db_id`-scoped in Postgres, matching the existing storage split.

## Non-goals (v1)

- **Suggested actions** ("update this wiki", "review these atoms"). A finding
  is prose with citations. Acting on it is the user's job.
- **Multiple findings per run.** One atom per run. If a "weekly contradiction
  scan" surfaces three contradictions, that is one atom listing three, not
  three atoms.
- **Event-driven triggers.** Schedule + manual-run only. Frequency is set by
  humans, which structurally bounds noise.
- **Wiki update from findings.** Reports write finding atoms plus their
  citation/provenance metadata, but never mutate wiki articles or other
  user-authored artifacts.
- **Outbound integrations.** Reports operate over the local knowledge graph;
  no external services, no outbound credentials.
- **Multi-step DAGs / step replay.** A report run is one bounded agent loop
  using the existing tool set.

## Conceptual model — the dual primitive

- **Wiki**: stateful synthesis under a tag. Converges. *"What we know about X,
  kept current."* Updated incrementally as atoms accrue.
- **Report**: dated investigation over a scope. Accrues. *"What did we find
  when we asked Q in window W?"* Each run is its own historical artifact.

Wikis converge; reports accrue. Findings are first-class atoms so the
substrate composes with itself — March's finding becomes April's context on
the same retrieval surface as any captured atom. This composition is the
point; it is also the reason the `kind` discipline below is non-optional.

## Prerequisite: the `kind` column on atoms

Findings cannot land before `kind` ships, and `kind` is not useful as a
column that exists but isn't enforced. The wiring must precede the first
non-`captured` atom.

```sql
ALTER TABLE atoms ADD COLUMN kind TEXT NOT NULL DEFAULT 'captured';
-- 'captured' = user-authored or imported (every existing atom)
-- 'report'   = emitted by a report run
CREATE INDEX idx_atoms_kind ON atoms(kind);
```

Existing atoms migrate to `'captured'` via the default. No data movement.

### Filter discipline

| Consumer | Default kinds | Rationale |
|---|---|---|
| A report's `semantic_search` tool | `report.context_include_kinds` (default `['captured']`) | First-hand research is the common case; chaining off prior findings is opt-in per report |
| Wiki generation (regen + incremental) | `['captured']` | The encyclopedia rests on first-hand knowledge |
| Auto-tagging pipeline | `['captured']` | Findings are stamped via `output_atom_tags`; auto-tag should not invent new categories from agent prose |
| Embedding pipeline | all | Findings are searchable substrate |
| Semantic-edge builder | all | Findings can participate in the graph |
| Canvas | all (visually differentiated) | Findings are part of the graph the user navigates |
| Search UI | all (visually differentiated) | User-facing search should reveal everything |
| Tag listings | all | Tags apply equally |

The implementation rule that prevents drift: every storage method that
returns atoms *for context assembly* (as opposed to user-facing display)
takes `kinds: &[AtomKind]` as a **non-defaulted** parameter. The compiler
forces every call site to decide. UI-display methods are separate APIs and
return all kinds by default.

## Schema

```sql
-- Per-DB. Data databases only — never registry.db.
CREATE TABLE reports (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    description          TEXT,
    research_prompt      TEXT NOT NULL,

    -- Source scope: the primary evidence set for the run.
    source_scope_tag_ids TEXT NOT NULL DEFAULT '[]',  -- JSON array of root tag ids (recursive)
    source_scope_window  TEXT,                         -- 'since_last_run' | ISO-8601 duration ('P7D', 'PT24H') | NULL
    source_include_kinds TEXT NOT NULL DEFAULT '["captured"]',

    -- Context scope: the corpus semantic_search may retrieve for comparison.
    -- context_scope_mode: 'same_as_source' | 'all' | 'explicit'
    context_scope_mode   TEXT NOT NULL DEFAULT 'all',
    context_scope_tag_ids TEXT NOT NULL DEFAULT '[]',
    context_scope_window TEXT,                         -- 'older_than_source' | ISO-8601 duration | NULL
    context_include_kinds TEXT NOT NULL DEFAULT '["captured"]',

    -- Citation policy:
    -- 'source_only' = only source atoms may be cited (daily briefing shape)
    -- 'source_and_context' = semantic_search results are citable too
    citation_policy      TEXT NOT NULL DEFAULT 'source_only',

    -- Bounded execution. Defaults are applied by read helpers, not seed rows.
    max_source_atoms     INTEGER,                      -- NULL = default cap
    max_source_tokens    INTEGER,
    max_tool_iterations  INTEGER,

    -- Schedule: cron expression + IANA timezone (same shape used by the existing briefing schedule).
    schedule             TEXT NOT NULL,
    schedule_tz          TEXT,                         -- NULL = UTC

    enabled              INTEGER NOT NULL DEFAULT 1,

    -- Output stamping: tags applied to every finding atom this report writes.
    output_atom_tags     TEXT NOT NULL DEFAULT '[]',   -- JSON array of tag ids

    -- Fast-path cache; not source of truth. Authoritative state lives on the run ledger.
    last_run_at          TEXT,
    last_finding_atom_id TEXT,
    last_error           TEXT,

    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE INDEX idx_reports_enabled ON reports(enabled, last_run_at);
```

```sql
-- Per-DB. The cited-atoms join from a finding atom back to the atoms it referenced.
CREATE TABLE report_finding_citations (
    finding_atom_id TEXT NOT NULL,
    cited_atom_id   TEXT NOT NULL,
    position        INTEGER NOT NULL,   -- 1-indexed order of [N] marker in the finding
    excerpt         TEXT NOT NULL,      -- stable hover/details text from cited evidence
    PRIMARY KEY (finding_atom_id, cited_atom_id, position),
    FOREIGN KEY (finding_atom_id) REFERENCES atoms(id) ON DELETE CASCADE,
    FOREIGN KEY (cited_atom_id)   REFERENCES atoms(id) ON DELETE CASCADE
);

CREATE INDEX idx_finding_citations_cited ON report_finding_citations(cited_atom_id);
```

Citations get their own join table rather than abusing `semantic_edges`
(which is similarity-derived, not authored) or stuffing markdown links into
the atom body (which makes "which findings reference atom X" unqueryable).
The excerpt is stored now, matching the existing briefing citation behavior,
so future citation-hover and "why was this cited" views do not need to
reconstruct old snippets from mutable atom content.

```sql
-- Per-DB. Durable provenance from report definitions to their finding atoms.
CREATE TABLE report_findings (
    finding_atom_id       TEXT PRIMARY KEY,
    report_id             TEXT,
    run_id                TEXT,          -- task_runs id when retained; no FK because run rows can be GC'd
    report_name_snapshot  TEXT NOT NULL,
    created_at            TEXT NOT NULL,
    FOREIGN KEY (finding_atom_id) REFERENCES atoms(id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
);

CREATE INDEX idx_report_findings_report_created
    ON report_findings(report_id, created_at DESC);
```

`task_runs.result_id` remains useful execution metadata, but it is not the
authoritative provenance link because run rows are subject to retention. The
dashboard, report history, deletion behavior, and same-report self-exclusion
all read `report_findings`.

### Source scope vs context scope

Reports have two scopes because some investigations are asymmetric:

- **Source scope** is the batch the run is primarily about. Daily briefing uses
  recent captured atoms. A contradiction scan uses newly captured atoms.
- **Context scope** is the corpus the report agent may search for comparison.
  Daily briefing can search the full captured corpus for background, while a
  contradiction scan usually searches older captured atoms, often under the
  same tag roots.

`citation_policy` decides which retrieved atoms may become formal citations:

| Report shape | Source | Context | Citation policy |
|---|---|---|---|
| Daily Briefing | recent captured atoms | all captured atoms | `source_only` |
| Weekly contradiction scan | recent captured atoms | older captured atoms, same tags or all | `source_and_context` |
| Open-questions status | tagged recent/open-question atoms | same tag subtree, older captured atoms | `source_and_context` |

The generalized `semantic_search` tool is parameterized by the resolved
context scope. When `citation_policy = 'source_only'`, search results are
background only and cannot be cited. When `citation_policy =
'source_and_context'`, search results are added to the run's citable evidence
map and may be cited by `[N]` markers. The LLM never decides this policy; the
runner enforces it.

### Dashboard featured-report pointer

```
Per-DB setting key: 'dashboard.featured_report_id' = <report id>
```

Stored in the data DB's `settings` table via the direct `core.storage()`
path, not via the registry-routed `get_settings` — the value is per-DB. On
DB creation: seeded to the id of the default report (below). If the featured
report is deleted, the setting is cleared and the dashboard renders an empty
state with a report picker.

### Per-DB seeding

On data-DB creation (and on migration for existing DBs), seed one report:

```
name:             "Daily Briefing"
description:      "Synthesizes recently captured atoms each morning."
research_prompt:  <the existing briefing system prompt, lightly revised>
source_scope_tag_ids: []
source_scope_window:  "since_last_run"
source_include_kinds: ["captured"]
context_scope_mode:   "all"
context_scope_tag_ids: []
context_scope_window: null
context_include_kinds: ["captured"]
citation_policy:  "source_only"
schedule:         <inherited from existing briefing-schedule setting>
schedule_tz:      <inherited from existing setting>
output_atom_tags: ["Reports/Briefings"] -- tag id, created if absent
enabled:          1
```

The seeded report is fully editable and deletable — there is no "system row"
status. The only thing that makes it "the briefing" is the dashboard
featured-report pointer.

## Execution ledger — `task_runs`

The reports primitive needs a durable, claim-with-lease, retry-with-backoff,
crash-recoverable execution substrate. This section specifies the minimum
viable version reports requires. It is a per-DB table, written by the
scheduler when a run starts and read by the same scheduler to gate
due-checks: no row for this report → due; pending row with
`next_attempt_at > now` → not yet; running row with `lease_until > now` →
already in flight.

For v1 reports are the only writer. The table is structured to absorb other
background work later (the existing `daily_briefing`, `draft_pipeline`, and
`graph_maintenance` tasks all have the same latent retry-storm shape this
table fixes, and the briefing in particular retrofits onto the ledger as
part of phase 3 because the briefing *becomes* a report). The other two
system tasks retrofit when convenient; that work is independent of
reports landing.

### Schema

```sql
-- Per-DB. Data databases only — never registry.db. Ships for SQLite and
-- Postgres in the same phase, mirroring the rest of the storage split.
CREATE TABLE task_runs (
    id              TEXT PRIMARY KEY,            -- uuid
    task_id         TEXT NOT NULL,               -- reports.id (v1: always a report id)
    subject_id      TEXT,                        -- NULL for reports; reserved for future per-subject tasks
    state           TEXT NOT NULL DEFAULT 'pending',
                                                 -- pending | running | succeeded | failed | abandoned
    trigger         TEXT NOT NULL,               -- 'schedule' | 'manual'
    attempts        INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 3,
    lease_until     TEXT,                        -- ISO-8601; canonical lock (in-memory lock is fast-path only)
    next_attempt_at TEXT NOT NULL,               -- backoff lives here
    scope           TEXT,                        -- resolved scope snapshot (JSON: tag ids, atom count, window)
    result_id       TEXT,                        -- finding atom id on success; convenience, not authoritative — report_findings is
    last_error      TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX idx_task_runs_claim   ON task_runs(state, next_attempt_at);
CREATE INDEX idx_task_runs_lease   ON task_runs(state, lease_until);
CREATE INDEX idx_task_runs_history ON task_runs(task_id, subject_id, created_at);
```

### State machine

- `pending → running` on claim: set `lease_until = now + lease_duration`,
  `started_at`, `state = 'running'`. The update is conditional on
  `WHERE id = ? AND state = 'pending'` (or `state = 'running' AND
  lease_until < ?` for the crash-recovery branch) so two claimants cannot
  both win.
- `running → succeeded` (terminal): set `result_id`, `finished_at`,
  `state = 'succeeded'`. Advance the report's `last_run_at` fast-path in
  the same transaction as the finding-atom write (see Execution model).
- `running → failed` then either:
  - `attempts < max_attempts`: back to `pending`, `attempts += 1`,
    `next_attempt_at = now + backoff(attempts)`, clear `lease_until`.
  - `attempts >= max_attempts`: `abandoned` (terminal). The next scheduled
    tick may insert a fresh `pending` row; the abandoned row is history.
- **Crash recovery.** A `running` row with `lease_until < now` is
  reclaimable. The claim path selects on
  `state = 'running' AND lease_until < ?` exactly like a pending row, and
  re-sets lease and `started_at`. `attempts` is *not* incremented on
  reclaim (we don't know whether the run completed and only failed to
  transition state — incrementing would punish a process crash as if it
  were a logic failure).

### Backoff

Exponential with jitter: `backoff(n) = base * 2^(n-1) * rand(0.5, 1.5)`,
with `base = 60s` and capped at `1h`. The cap matters because some reports
will run on schedules tighter than an hour, and the backoff should not
overshoot the next scheduled fire.

### Claim flow per scheduler tick

For each enabled report:

1. Look for an existing runnable row:
   ```sql
   SELECT id FROM task_runs
   WHERE task_id = ?
     AND (
         (state = 'pending' AND next_attempt_at <= ?)
      OR (state = 'running' AND lease_until < ?)
     )
   ORDER BY next_attempt_at ASC
   LIMIT 1;
   ```
2. If found, attempt the conditional claim update; on success, run.
3. If no runnable row, evaluate due-check against the report's cron
   expression and `last_run_at` fast-path. If due, insert a fresh
   `pending` row with `next_attempt_at = now`, then loop back to step 2.
4. The in-memory `(task_id, db_id)` lock from the existing scheduler
   demotes to an optimization that skips the DB round-trip when a run is
   already known to be in flight in this process. Correctness lives in
   `lease_until`.

### Lease duration & heartbeat

15 minutes. Long enough that a slow LLM-with-tools report run does not
expire mid-execution; short enough that crash recovery is timely. The
runner refreshes the lease (`lease_until = now + 15m`) every 5 minutes
from inside `run_report` so a genuinely long-running report does not lose
its claim. If the heartbeat itself fails, the next scheduler tick will
reclaim the row after the lease elapses.

### Out of scope for v1 (deliberately deferred)

- **Retention / GC.** Five reports running daily produce ~150 rows/month.
  Table size is a non-issue for the first months of v1; GC ships when
  warranted, not pre-emptively. The intended future policy is sketched
  below so the eventual addition isn't a fresh design.
- **System-task retrofit beyond the briefing.** `draft_pipeline` and
  `graph_maintenance` continue using their existing scheduling.
  Retrofitting them onto the ledger fixes their own latent retry-storm
  bug but is independent of reports and ships when convenient.
- **Feed polling fold-in.** Untouched. Independent design.
- **Step-level replay / activity layer.** Run granularity stops at "the
  run." Tool calls inside the agent loop are not persisted as separate
  rows.

### Future retention policy (for reference, not built in v1)

When GC ships: per `(task_id, subject_id)`, keep the most recent K
terminal rows (default `K = 50`) and always retain the most recent
terminal *failure* per `(task_id, subject_id)` regardless of K (failures
are rare and high-value). Hard age caps: 30 days for successes, 90 days
for failures. Deletes happen in 500-row batches to avoid holding the
write lock against user atom edits. GC is itself a scheduled task — same
loop, same ledger, its own bounded history.

## Execution model

Each report run is one row in the per-DB `task_runs` ledger specified
above. `task_id = <reports.id>`, `subject_id = NULL`,
`trigger = 'schedule' | 'manual'`, `result_id = <finding atom id>` on
success. `result_id` is convenience metadata only — the authoritative
report → finding link lives in `report_findings`, which outlives the
ledger row through future GC.

### Lifecycle of one run

1. **Due check.** The scheduler tick evaluates each enabled report against
   its cron expression and `last_run_at` fast-path. Due reports get a
   `pending` ledger row (or reclaim an existing retryable one).
2. **Claim.** Lease the row.
3. **Resolve source and context scopes.** Compute the source atom set:
   - Filter by `source_scope_tag_ids` (recursive over tag subtrees), if any.
   - Filter by `source_scope_window`:
     - `null`: no time bound.
     - `"since_last_run"`: `atoms.created_at > reports.last_run_at` (or
       `0` if never run).
     - ISO-8601 duration: `atoms.created_at > now - duration`.
   - Filter by `source_include_kinds`.
   - Apply `max_source_atoms` / `max_source_tokens` caps before prompting.
   - **Empty scope is a terminal no-op success.** Don't write empty
     findings. Advance `last_run_at`; record a brief reason on the run row;
     do not create an atom.
   - Resolve the context scope separately from the source scope. For
     `context_scope_window = 'older_than_source'`, semantic_search excludes
     source atoms and only searches atoms older than the source window cutoff.
4. **Run the agent.** The same agentic loop the briefing uses today
   (`read_atom`, `semantic_search`, `done`), generalized:
   - The system prompt scaffolds citation conventions, length expectation,
     and output schema. The report's `research_prompt` is composed into it
     as the *ask* (the "what to investigate" body).
   - The `semantic_search` tool is parameterized by the context scope and
     `context_include_kinds`. Default `['captured']` keeps findings out of
     context unless the report opts in. A "weekly contradictions meta-review"
     can opt in to `['captured', 'report']` to chain off prior research.
   - For `citation_policy = 'source_only'`, `[N]` markers may only resolve to
     source atoms. For `source_and_context`, search results are assigned
     citation numbers as they are surfaced and may be cited alongside source
     atoms.
   - The citable-evidence map is run-scoped and append-only. Source atoms
     receive their `[N]` numbers up front in scope-resolution order; under
     `source_and_context`, each `semantic_search` result is assigned the next
     available number on first appearance and reused thereafter, and every
     tool response surfaces the (already-assigned or newly-assigned) number
     alongside each result. This way an `[N]` reference resolves
     unambiguously regardless of when in the run it was emitted, and the
     runner — not the agent — owns the numbering.
   - To prevent the most degenerate self-feedback loop, `semantic_search`
     excludes the finding atoms produced by *this same report definition*
     even when `'report'` is included.
5. **Write the finding atom transactionally.**
   - `kind = 'report'`.
   - Body = the agent's prose, with `[N]` citation markers as today.
   - Tags = `output_atom_tags`, applied at write time. Auto-tagging is
     skipped for `kind = 'report'` atoms (see filter table).
   - The atom enters the standard embedding pipeline; semantic edges build
     normally. Auto-tagging does not run.
   - Insert the `report_findings` provenance row in the same transaction.
6. **Record citations.** Each `[N]` marker resolves to an atom id from the
   run's citable evidence map; rows insert into `report_finding_citations`
   with marker position and excerpt.
7. **Terminal transition.** Run row → `succeeded`, `result_id` =
   finding-atom id. `reports.last_run_at` and `last_finding_atom_id`
   updated. The atom write, tag stamping, provenance row, citation rows,
   report cache update, and run success transition should be exposed as one
   storage helper after the LLM returns so a crash cannot leave orphan report
   atoms or succeeded runs without citations.

Manual runs use the same machinery and store `trigger = 'manual'` on the run
row. A normal "run now" advances `last_run_at` just like a scheduled success.
Future backfill/preview modes, if added, should be explicit separate triggers
that do not advance the schedule fast-path.

## Briefing collapse — proving the abstraction

Once the report runner exists and the seeded default report runs end-to-end
on a fresh DB, the existing hardcoded `daily_briefing` task is removed in
the same change:

- The hardcoded `briefing` module's execution path is replaced by the
  generalized `reports::run_report`. The briefing system prompt becomes the
  default report's `research_prompt`.
- The existing per-DB `briefings` table (which today stores briefing
  artifacts) is migrated: each row becomes an atom with `kind = 'report'`,
  `created_at` preserved, tagged with `Reports/Briefings`, with a
  `report_findings` provenance row pointing at the seeded Daily Briefing
  report, and with citations rehydrated into `report_finding_citations`
  where the data permits. The `briefings` table is then dropped.
- The dashboard's briefing view changes data source: it reads recent finding
  atoms produced by `dashboard.featured_report_id`, rather than the dropped
  `briefings` table. The user can re-point the dashboard to any other
  report.

The hardcoded `briefing_prompt` setting becomes an initialization input
(used to populate the seeded report's `research_prompt`), not an ongoing
live setting; editing the prompt afterward edits the report row.

## External consumers — Obsidian plugin and beyond

The Obsidian plugin (`plugins/obsidian-plugin`) syncs atoms back into the
user's vault as markdown files. The moment report-kind atoms start being
written — and especially when phase 3 migrates historical briefings into
atoms — every finding would land in the vault as a file unless the sync
opts out. That is a product break (notes the user did not write appearing
in their vault), not a code break. The same exposure applies to any future
consumer that materializes atoms into an external store: a different MCP
client doing exports, a future mobile sync, third-party API users.

The fix ships **in phase 3, alongside the briefing collapse**, not later:

- **Server.** The atom-list endpoints that external consumers use accept an
  optional `?kinds=` query parameter (CSV of `AtomKind` values: `captured`,
  `report`). Default behavior is unfiltered — preserves backward
  compatibility for any caller that does not yet know about `kind`. Filtered
  behavior is opt-in. This mirrors how `scope_tag_ids` / `created_after` are
  already optional filters on the search endpoints.
- **Obsidian plugin.** The sync engine passes `?kinds=captured` on its pull
  and any related list requests. Report atoms never enter the vault by
  default. A plugin-side setting can later expose this as a user choice
  ("sync report findings into your vault: off / on") for users who *do*
  want findings as Obsidian files — but the safe default ships first.
- **API contract.** Adding `kind` to the atom JSON response is backwards
  compatible (extra field, no removals) and does not require a coordinated
  plugin release for phase 1; the plugin's TypeScript types ignore unknown
  fields. The coordinated release happens with phase 3, when the new query
  parameter starts being meaningful.

The hard prereq for phase 3 is therefore: the `?kinds=` parameter is live
on the server *and* the published plugin version is passing
`?kinds=captured` *before* the first report finding atom is written on any
user database (i.e., before the briefing collapse cuts over). The seeded
default report on a fresh DB does not begin running until that condition
holds.

## Phasing

Each phase is independently shippable.

1. **`kind` column + filter wiring.** Migration adding `kind` defaulting to
   `'captured'`. Every storage call site updated to take an explicit
   `kinds: &[AtomKind]`. Wiki generation, semantic-edge building, auto-tag,
   embedding, search, and canvas all audited. No behavior change for end
   users yet — all atoms are still `captured`.
1.5. **Execution ledger.** `task_runs` table and the claim / lease /
   crash-recovery helpers in both SQLite and Postgres storage, per
   *Execution ledger* above. No new consumers yet — reports will be the
   first writer in phase 2. The existing scheduler tick gains the
   claim-and-record path but continues to spawn the legacy system tasks
   the way it does today (their retrofit is independent polish, except
   for the briefing in phase 3). Tests cover the state machine, backoff,
   conditional-update contention, and crash-recovery reclaim.
2. **Reports primitive.** `reports`, `report_findings`, and
   `report_finding_citations` tables in both SQLite and Postgres storage.
   `reports::run_report` generalized from the briefing runner. Run rows
   land in the phase-1.5 ledger. Manual-run path available; scheduled-run
   plumbed through the scheduler tick.
3. **Briefing collapse.** Seed the default "Daily Briefing" report on every
   existing DB (idempotent if already present). Cut the briefing execution
   over to `reports::run_report`. Migrate the `briefings` table into
   finding atoms and drop it. Dashboard reads from `featured_report_id`.
   Ship the `?kinds=` query parameter on the atom-list endpoints and a
   coordinated Obsidian plugin release that passes `?kinds=captured` from
   the sync engine, per *External consumers* above — both must be live
   before the first finding atom is written.
4. **Report authoring UX.** Create / edit / enable-disable / run-now / view
   history. Build on the schedule UI already in place for the briefing
   (TZ-aware, next-run preview). Dashboard featured-report picker.
5. **Curated templates.** A small set of starter reports the user can adopt:
   weekly contradiction scan, open-questions status, themes-this-month,
   orphan-detection. Each ships as a JSON template the UI can instantiate
   into a `reports` row; the templates are not seeded automatically.

Phase 1 is the load-bearing one. The rest is incremental on top of it.

## Risks & mitigations

- **`kind` filter inversion.** A context-assembly call site that silently
  defaults to "all kinds" would quietly contaminate a downstream synthesis
  with agent output. *Mitigation:* non-defaulted `kinds` argument on every
  storage method that returns atoms for context. `AtomKind` is a real Rust enum
  used at API boundaries; SQL string values stay contained at the storage
  boundary. Audit checklist before phase 1 lands.
- **Self-feedback loop.** A report that opts into `context_include_kinds`
  containing `'report'` could find its own previous finding as relevant context.
  *Mitigation:* `semantic_search` always excludes finding atoms produced by
  the running report's own definition using `report_findings`; cross-report
  chaining remains allowed.
- **Asymmetric search ambiguity.** Contradiction and open-question reports need
  to compare a source batch against a different context corpus. *Mitigation:*
  source scope and context scope are separate fields, and citation policy
  controls whether context search results are citable.
- **Finding-atom tag bloat.** If auto-tagging runs on findings, the LLM
  categorizer will invent tag children from the finding's prose. *Mitigation:*
  auto-tagging skipped for `kind = 'report'`. Findings are tagged
  deterministically via `output_atom_tags`.
- **Empty-scope spam.** A report that wakes up to an empty scope must not
  write a finding ("Nothing to report."). *Mitigation:* explicit empty-scope
  short-circuit at step 3 of the lifecycle; no atom written; run row
  terminal-success with reason.
- **Retry storm without backoff.** A failing report on a tight schedule
  could re-fire indefinitely — the same latent bug the existing system
  scheduler has today. *Mitigation:* the `task_runs` ledger gates claims
  on `next_attempt_at <= now`; failed runs back off exponentially with
  jitter, capped at 1h; after `max_attempts` the run is `abandoned` and
  the next scheduled tick re-pends fresh. Backoff and crash-recovery
  semantics live in *Execution ledger* and are tested in phase 1.5
  before reports can write a run.
- **Lease starvation on long runs.** A slow LLM-with-tools report could
  exceed the 15-minute lease and have a concurrent reclaimer start a
  duplicate run. *Mitigation:* the runner heartbeats the lease every 5
  minutes from inside `run_report`; the conditional-update claim query
  prevents two claimants from both transitioning a `pending` row to
  `running`.
- **Reclaim-as-failure attribution.** A process crash mid-run would, if
  `attempts` were incremented on reclaim, eventually `abandon` a report
  that never actually had a logic failure. *Mitigation:* reclaim re-sets
  the lease and `started_at` but leaves `attempts` unchanged.
- **Briefings-table migration data loss.** Existing briefing artifacts must
  arrive intact in atoms. *Mitigation:* phase 3 ships the migration with a
  pre-flight count + post-flight reconciliation; the drop of `briefings`
  is the last step of the phase, not the first.
- **Multi-DB regressions.** Reports, citations, the featured-report
  pointer, and the seeded default report are all per-DB. *Mitigation:* all
  reads/writes go through `core.storage()`, not the registry-routed
  settings shortcut; default-report seeding is part of the data-DB
  initialization path; the scheduler's `manager.list_databases()` fan-out
  is reused unchanged.
- **Postgres drift.** A SQLite-only implementation would silently break the
  shared-infrastructure storage backend. *Mitigation:* every schema and store
  operation added for reports ships for SQLite and Postgres in the same phase;
  Postgres rows are `db_id`-scoped just like existing atom/wiki/briefing
  storage.
- **External-store contamination via sync clients.** Without an opt-out
  filter on atom-list endpoints, the Obsidian plugin would sync report
  findings into the user's vault as markdown files, and any future
  external consumer would do the same. *Mitigation:* the `?kinds=` query
  parameter on atom-list endpoints and the coordinated plugin release
  passing `?kinds=captured` from the sync engine both ship in phase 3
  before the first finding atom is written. See *External consumers* above
  for the full contract.

## Resolved decisions

1. **One finding-atom per run.** No multi-finding output. Simpler schema,
   clearer UX, single citation set per artifact.
2. **`kind` ships in phase 1 with the column and the wiring**, before any
   non-`captured` atom can be written. Two-value enum: `captured` |
   `report`. No `'briefing'` kind.
3. **Schedule-only triggers for v1.** No event-driven, no threshold.
4. **Findings are atoms.** Single substrate, gently typed. Composition is
   the point. The filter table is the discipline that makes it safe.
5. **Citations live in their own join table.** Not in similarity edges, not
   only in markdown body. Citation rows store excerpts.
6. **The briefing is just a report.** No `system_key`, no privileged row.
   The dashboard's featured-report pointer is the only thing that picks
   "the briefing" out of the set, and the user can re-point it.
7. **Reports are database-scoped.** Each data DB seeds its own default
   report on creation.
8. **`source_scope_window = 'since_last_run'`** is supported alongside ISO
   durations — it's the natural shape for self-pacing reports and the
   briefing's existing semantics.
9. **Source and context scopes are distinct.** `semantic_search` searches the
   context scope, not necessarily the source scope. This supports asymmetric
   report shapes like "find contradictions between new atoms and older notes."
10. **Finding provenance is durable.** `report_findings` is the authoritative
    report→atom link; `task_runs` remains execution history.
11. **The execution ledger is part of this plan, not a separate one.** A
    minimum-viable `task_runs` table (claim, lease, crash recovery,
    retry/backoff) ships in phase 1.5, scoped to what reports needs. GC,
    feed-poll fold-in, and the non-briefing system-task retrofits are
    independent follow-ups, not blockers.

## Open questions

1. **`read_atom` scope-filtering.** `semantic_search` is scope-filtered by
   `context_*` fields; `read_atom` today accepts any atom id the agent has
   seen. Should `read_atom` be restricted to the resolved citable-evidence
   map (preventing the agent from following ids it learned through other
   channels), or stay open as it is today? Tentative: stay open — the agent
   can only see ids that came from search results or the source list anyway,
   so the additional restriction has no current attack surface.
2. **Wiki integration (suggested updates from findings).** Punted to v2.
   The shape that will probably want to exist: a finding can declare a
   suggested wiki update, surfaced as an action the user accepts or
   dismisses. Not in v1.
3. **Auto-tagging opt-in for reports.** Currently disabled for `kind =
   'report'`. A future per-report flag could re-enable it for reports whose
   findings are sufficiently topical and want graph discovery beyond the
   stamped tags. Not in v1.
