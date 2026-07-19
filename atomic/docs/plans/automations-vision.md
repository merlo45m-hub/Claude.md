# Automations & Integrations — Vision

> Scope: the *vision* for Atomic's automation surface. It sits on top of the
> durable execution substrate specified in
> [`durable-task-runs.md`](./durable-task-runs.md) (referred to as **L0**).
> This doc does not re-derive the `task_runs` schema; it depends on it.
>
> **This document was deliberately narrowed.** An earlier draft centered on an
> external-integration agent orchestrator (scheduled multi-step tasks over
> OAuth'd third-party services, e.g. "Meeting Prep"). That direction was
> consciously rejected — see *Deliberately not building* and *Accepted
> tradeoff*. The vision is now: **Atomic is a reactive knowledge substrate, not
> an orchestrator.**

## Context

Atomic does a few things automatically: embed, auto-tag, briefings, RSS sync —
each a bespoke hardcoded loop with little user control. The opportunity is to
generalize the ones that are *Atomic's job* into a small composable model, and
to explicitly *not* build the ones a user's trusted agent host already does
better.

The decisive realization: Atomic already exposes an MCP server, so its
knowledge graph is already reachable from any agentic host (Claude Code,
Claude Desktop, etc.). Those hosts already have scheduling, an agent loop, tool
calling, and — critically — they already solve outbound credential custody,
because the user connects external services to a host they trust *more than
Atomic*. Anything in the "scheduled, agentic, uses my external accounts" class
is therefore something the host does better, with the credential problem
already solved. Atomic building that = re-implementing the host badly while
assuming the worst custody liability for the least differentiated value.

## Guiding principles

> **1. Composable primitives, not a flow builder.** Users assemble automations
> from a small fixed vocabulary. The agent decides *what to do*, never *when*
> or *over what*. Trigger and scope are always structured.
>
> **2. Substrate, not orchestrator.** Atomic builds only automations that are
> data-adjacent and event-driven — the things that have *no host substitute*.
> External, scheduled, multi-step orchestration is the host's job. Atomic's
> job is to be the substrate the user's trusted host orchestrates.

## The dividing line (the organizing decision)

Place every candidate automation on one axis: **how data-adjacent and
event-driven is it?**

| | **Atomic builds it** | **The host owns it** |
|---|---|---|
| Trigger | Internal lifecycle event (atom embedded, edge built, threshold crossed) | External schedule / user-initiated |
| Data coupling | Transactional, in-process, no polling | Coarse MCP tool calls |
| Runtime | Always-on, server-side, every device, no host attached | Only when that host + machine + config is up |
| External auth | None | The host's (the user's own, already trusted) |
| Who it serves | **Every** user, incl. desktop/mobile/non-developers | Power users with a configured agent host |

The far-left column is work a host *structurally cannot do*: it has no hook
into "embedding just completed for atom X," it doesn't run on the user's phone
with no host attached, and it doesn't exist at all for the non-developer who
will never wire up a cron. The far-right column is work a host *already does
better*. Atomic builds the left column and invests in being orchestrated for
the right.

**The interlock that settles it:** the users for whom "just use your trusted
host" works painlessly are exactly the users whose credential problem is
already solved; the users who'd benefit from Atomic doing external
orchestration are exactly the host-less ones for whom credentials are hardest
and unsolved. The value and the hardest cost of external orchestration are
concentrated in the same segment — which is why it's a bad place to invest.

## The layer stack

| Layer | What it is | Status |
|------|------------|--------|
| **L0** | Execution substrate — `task_runs` | `durable-task-runs.md` |
| **L1** | Definition model — `automations` table, **event-driven first** | This doc |
| **L2** | Action vocabulary — fixed set + `agent.run` (**internal tools only**) | This doc |
| **L3** | Surface for external hosts — Atomic-as-MCP-server excellence | This doc |
| **L4** | Trust & safety | This doc |
| **L5** | Authoring UX | This doc |

L4 rides on L0: "run history / did it retry / why did it fail" *is* the
`task_runs` ledger. Building durability first is what makes trust mostly free.

## L1 — Definition model

A per-DB `automations` table: `trigger`, `scope`, `action`, `capabilities`,
`enabled`, idempotency `cursor`. Each firing produces a `task_runs` row with
`task_id = <automation id>` — no L0 schema change.

**Privileged core stays code; user automations are strictly additive.**
Embed/auto-tag/briefing/feed-sync stay code-defined and privileged (load-
bearing for search correctness), shown in the UI as read-only system rows.

**Event-driven first.** Triggers, in priority order:

- `atom.{created,updated,embedded,tagged}`, `edge.built`, `wiki.regenerated`
  — internal lifecycle, no polling, transactional with the data. *This is the
  moat.*
- `threshold(scope, n)` — debounce on accumulation (cursor per (automation,
  db), the L0 shape). Pairs with briefings.
- `schedule(cron)` — retained for briefings and digests, but explicitly the
  *least* differentiated trigger; not the center of gravity.

Filter vocabulary stays deliberately tiny (tag-subtree membership, source id,
maybe content regex). Arbitrary boolean predicates = Zapier; hold the line.

**Scope** is usually a tag subtree (reusing wiki/chat resolution); for event
triggers it is typically the triggering atom's semantic neighborhood. Show the
resolved item count before save.

## L2 — Action vocabulary

Fixed set, all internal: `wiki.regenerate` · `wiki.update_incremental` ·
`atom.create` · `atom.annotate` · `embed` · `retag` · `notify`.

`agent.run(instruction)` is the LLM-native escape hatch — structured trigger
and scope, free-text body, **internal tools only** (`semantic_search`,
`read_atom`, etc.). No external MCP tools. Bounding principle: each run is a
single bounded unit (one scope, token ceiling, no human-in-the-loop, no
fan-out). If a recipe needs durable multi-step orchestration, that is the
tripwire that it has grown too ambitious — and likely belongs in the user's
host, not Atomic.

## L3 — Surface for external hosts (inverted from the old plan)

The old L3 made Atomic an MCP *client* with outbound OAuth. **Removed.**
Replaced with: make Atomic's MCP *server* surface excellent so the user's
trusted host can orchestrate it.

- Rich MCP **resources** over the knowledge graph (atoms, tags, wikis, search).
- **Event / subscription exposure** so a host agent can react to "atom tagged
  X" without polling — Atomic pushes, the host orchestrates.
- High-quality tools (search, create, annotate) for host-driven workflows.

**Inbound vs outbound — the precise technical line.** The cut is *outbound
credential custody*, not all integration:

- **Kept:** RSS (public, unauthenticated pull) and webhook-*push-in*
  (authenticated by Atomic's own existing inbound token — no new custody). A
  light `Source` trait may still generalize RSS.
- **Cut/deferred:** anything where Atomic must hold a secret to authenticate
  *outbound* to a third party — `McpSource` polling an external server,
  outbound `emit` to external services, OAuth client implementation. That is
  the host's job.

## L4 — Trust & safety

- **Per-automation capability allowlist** — the real safety boundary. With
  external tools gone, the surface is dramatically smaller: internal tools
  only, default-deny `atom.delete`.
- **Dry-run / preview** — actions as *proposed effects* before commit (command
  pattern). Non-determinism without preview burns trust on the first bad run.
- **Per-run token ceiling** — runaway agent loop → terminal `budget_exceeded`.
- **Idempotency cursor** — belongs to the definition, not the run row.
- **Run history** — *is* the `task_runs` ledger (L0).

## L5 — Authoring UX

"**When** \<structured trigger\> **over** \<structured scope\>, the assistant
**will**: \<free text\>." Capability toggles, not tool names. "Test now" =
dry run. Resolved scope count before save. System automations appear as
read-only rows.

## Flagship — Tension Surfacing on Write

The example the vision is built around, reasoned through end to end — because
it is both the proof of the moat and the *template* for the whole in-scope
class.

### The value

The thing a human cannot do for themselves: notice when they are contradicting
their *past* self. Not because the judgment is hard, but because you don't
*remember* the old note exists — the contradiction is invisible in exact
proportion to how long ago you wrote it, and keyword search can't help because
if you knew the keyword you'd remember the note. This is the literal promise of
a second brain that most tools fake with backlinks and never deliver.

### Why only Atomic — all three must hold at once

(a) a semantic graph to find the *one* relevant prior atom out of thousands
with no shared keywords; (b) a hook on the **internal embedding-complete
lifecycle** so it fires sub-second after save with no polling; (c) it runs
server-side on every device with no agent host attached. A host cron fails (b)
and (c) outright and does not exist for the non-developer at all. Strip any one
and it collapses — the cleanest possible case for the narrowed scope.

### The trigger is a real design decision

`atom.created` is **wrong** and instructively so: the pipeline is async, so at
`created` time there are no embeddings and no neighborhood — nothing to compare
against. The correct trigger is `atom.embedded` / `edge.built`: the automation
is only meaningful *after the pipeline it depends on completes*. This is the
concrete proof of the L1 rule that triggers must be derived from real lifecycle
events, not invented. Detection is **from the changed atom's side only** (new
atom vs. its k-nearest neighbors); the transitive case (editing an old atom
makes two *other* atoms conflict) is explicitly out of scope. Every automation
in this class needs that "we do not chase the transitive closure" line.

### Why the action must be `agent.run`, not a heuristic

Scope = the triggering atom's top-k neighbors above the related-atoms
similarity threshold (~0.5). But similarity only yields *related* — it cannot
distinguish *agrees / elaborates / restates / contradicts / is-in-tension*.
That discrimination is **inferential, not retrievable**. This is the
irreducible reason the action is an LLM call: the automations that justify this
vision are exactly the ones where retrieval finds the candidates but only
judgment classifies them. Anything a heuristic could do, a host could do too.

### The part that decides whether it ships: the annoyance budget

Most semantically-near atoms are *not* contradictions; they are elaborations. A
naive build cries wolf on every save and is muted within a day — and a muted
feature is a deleted feature. The asymmetry is the whole game: a **missed**
contradiction is invisible (no felt harm); a **false** one is trust-destroying.
So this is tuned violently toward **precision over recall**, which is
counterintuitive because recall feels like the point. It is not. One real
tension a week with zero lies beats ten with two false positives. Concretely:

- Prompt the agent to default to **silence**; surface only genuine,
  high-confidence tension; emit a confidence rating; sub-threshold results are
  stored quietly, never notified.
- An **annoyance budget** as a first-class invariant: cap surfaced tensions per
  day; decay/back off if the user dismisses repeatedly. Only possible *because*
  L0 gives durable run + dismissal history — the substrate paying off in a
  non-obvious place.
- **Pair-aware idempotency.** The cursor is not atom-keyed, it is a
  **pair-keyed suppression set**: a dismissed `(atom_a, atom_b)` pair never
  resurfaces. Re-run on an unchanged atom = no-op (`atom_id + content_hash`);
  editing an atom re-opens it, but a dismissed pair stays suppressed unless the
  *other* atom also materially changed. Pin this before building.

### Cost, gated by the quiet-period idiom

Every qualifying save = one LLM call over k neighbors; for a heavy note-taker
mid-flow that is a cost disaster if naively event-driven. Mitigations are
existing codebase idioms: skip when the atom has zero neighbors above threshold
(and note — that "orphan" case is itself a *separate* in-scope automation:
"connects to nothing you know — new thread or mistag?"; they compose), and
reuse the `draft_pipeline` **quiet-period** so it never fires mid-typing. The
general lesson: naive event-driven is unviable; event-driven *plus debounce
plus durable dedupe* is the only viable shape — which is why L0 had to exist
first.

### The non-obvious product insight

When the "contradiction" is the user **deliberately changing their mind**, that
is not a false positive — it is the *highest-value* surfacing in the feature,
but only if framed as *"your thinking evolved here"* (curious, observational)
rather than *"ERROR: contradiction"* (corrective). The tone of the annotation
is load-bearing. This must feel like a thoughtful librarian who noticed
something, not a linter that failed your notes. Default to the **quiet
annotation discovered when you look**; reserve the **interrupting
notification** for high-confidence direct contradictions only.

### Why this generalizes (the real payoff)

The reasoning chain — internal-lifecycle trigger (not invented) → bounded
neighborhood scope (no transitive closure) → LLM judgment retrieval can't do →
precision-over-recall + annoyance budget + pair-aware dismissal + cost gated by
quiet-period — **is the repeatable template for the entire in-scope class**:
orphan detection, "your open question just got answered by a later note,"
tag-bifurcation/split suggestion, stale-conclusion decay, near-duplicate
detection. All share the shape. The narrowed scope does not just *permit* one
good feature; it *generates* host-impossible automations from one pattern. That
is the result: the scope is productive, not merely defensible.

Mapped to the stack: trigger `atom.embedded`; scope = triggering atom's
neighborhood; action `agent.run` with `semantic_search` + `read_atom` +
`atom.annotate` + `notify`; pair-keyed suppression cursor; history in
`task_runs`. Contrast the rejected Meeting-Prep flagship — scheduled,
external-OAuth, host-replicable — the exact profile we are *not* building.

### Open product decisions (not architecture)

The architecture is settled; what remains are product calls, which is itself a
good sign:

1. Annoyance-budget policy — fixed daily cap, or adaptive decay on dismissal?
2. Quiet-annotation-by-default vs. notification, and exactly where the
   confidence line for "interrupt the user" sits.
3. Whether "you changed your mind" is surfaced as tension at all, or as its own
   gentler category.

## Deliberately not building

**External-integration agent orchestration** (scheduled, multi-step tasks over
the user's OAuth'd third-party accounts — the Meeting-Prep class).

Rationale: a trusted agent host already does this better; its credential model
is the user's own and the host is a party the user trusts more than Atomic.
Building it means re-implementing the host badly while taking on the worst
custody liability for the least differentiated value, and its value/cost are
concentrated in the same host-less segment.

Instead, the path for users who want that: connect Atomic-as-MCP-server *and*
their external MCP servers to *their* trusted host, and let the host
orchestrate. Atomic supplies the knowledge substrate; the host supplies
orchestration and external credentials. L3 exists to make that path good.

### The credential problem — dissolved, not solved

We analyzed it fully (the inbound-verify vs. outbound-custody inversion;
Topology A "Atomic → provider" vs. Topology B "Atomic → MCP server →
provider"). Conclusion: **Atomic declines to be an outbound credential
custodian at all.** That deletes, from scope entirely: an OAuth 2.1 client,
DCR, refresh-token custody, per-deployment vault, and the per-tier
reconciliation with the hosting strategy. The hardest, highest-blast-radius
problem class is removed, not mitigated.

## Accepted tradeoff (consciously chosen)

Ceding external orchestration cedes the *visible external-integration magic* to
whoever owns the host — "my meeting got prepped" becomes a host story, not an
Atomic story. **This is accepted**, because:

1. The durable moat is the data-adjacent, event-driven magic that has no host
   substitute and serves *all* users — that is where differentiation actually
   lives.
2. It deletes the hardest and most dangerous problem class outright.
3. The broad non-power-user base is served by turnkey internal automations,
   not by external orchestration they would never set up.

Residual, flagged for the monetization/hosting plan: managed-tier
differentiation must rest on substrate quality, hosting convenience, and the
internal magic — **not** on external orchestration. This is the one place the
decision must be reconciled with the business model.

## Explicit non-goals

- No visual flow / node-graph editor.
- No arbitrary boolean predicate language.
- No multi-step DAGs / workflow orchestration; no step-level replay.
- No human-in-the-loop approval inside a run.
- **No external-integration agent orchestration; no outbound credential
  custody; no OAuth client.**
- Automations never become load-bearing for embed/auto-tag correctness.

## Phasing

L0 (`durable-task-runs.md`) is the prerequisite.

1. **L1 minimal** — `automations` table; `atom.*` event triggers + `schedule`;
   internal actions only; make briefing parameters user-editable (still a
   privileged system row).
2. **Flagship: Tension Surfacing** — `agent.run` (internal tools only) with
   capability allowlist, token ceiling, dry-run command pattern. This is the
   proof of the moat.
3. **L3 MCP-server surface** — rich resources + event/subscription exposure so
   external hosts can orchestrate Atomic; light `Source` generalization for
   RSS/webhook-push-in only.
4. **L5 authoring UX** — incremental; dry-run/"test now" lands with phase 2.

## Risks & mitigations

- **Commoditization** — accepted (see above); mitigation is owning the
  data-adjacent moat, not avoiding the tradeoff.
- **Filter vocabulary creep → Zapier** — treat boolean predicate requests as a
  design smell.
- **`agent.run` ambition creep** — the bounding principle is the tripwire;
  over-ambitious recipes belong in the user's host, not Atomic.
- **Multi-DB** — `automations`, cursors, runs are per-DB (L0 rules apply).

## Resolved decisions

1. **Substrate, not orchestrator.** Atomic builds data-adjacent, event-driven
   automations only; external scheduled orchestration is the host's job.
2. **Privileged core + additive automations.**
3. **The credential problem is dissolved** by declining outbound custody — no
   OAuth client, no external MCP client, no vault.
4. **Flagship is Tension Surfacing on Write**, not Meeting Prep.
5. **Commoditization of external magic is an accepted tradeoff**; differentiation
   rests on the internal moat + hosting, reconciled in the monetization plan.

## Open questions

1. **Managed-tier differentiation** without external orchestration — for the
   monetization/hosting plan, not this doc.
2. **MCP event/subscription exposure mechanics** — depends on MCP spec
   maturity; design when phase 3 starts.
3. **Threshold vs cron for briefings** — replace the fixed clock with
   accumulation-debounce, or coexist? (Carried from L0.)
