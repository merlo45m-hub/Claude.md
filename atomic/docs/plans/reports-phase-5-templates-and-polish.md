# Reports Phase 5 — Curated Templates + Polish

After 4c, every backend capability of the reports primitive has a UI
home. Phase 5 is the "feels finished" pass: curated templates that
give new users a starting point besides "stare at a blank prompt
field", plus targeted polish on the rough edges of 4a-4c.

This is the last phase of the reports work as currently scoped.
After 5, the feature is done. Future work (orphan detection, task-run
ledger view, bulk actions, retry-attempt config) waits for user
feedback.

## Goals

- A first-run user opens "New report" and sees four well-chosen
  starting points instead of an empty prompt field.
- Templates are the *content* the project commits to ship — they
  define what "good use of reports" looks like and seed the user's
  intuition for what to build next.
- The detail-view header doesn't visually break below 640px wide.
- The two custom dropdowns added in 4c (`FeaturedDropdown`,
  `ContextMenu` overflow on row) navigate by keyboard, not just mouse.

## Non-goals (v1)

- Backend-served template catalog. Templates ship as a TS constant;
  updates ride with app releases.
- Template authoring UI. The four templates we ship are what's
  available; users can't make their own template (they can save
  any report as a normal report, which is the practical substitute).
- Full a11y audit + focus-trap management on every modal. The
  dropdowns are the obvious gap; other surfaces use native controls
  that already keyboard-handle.
- Mobile pass on every reports screen. The detail-view header is the
  cramped one; ReportsList, FindingsList, the editor modal, and the
  dashboard widget are already at least passable on small viewports.

## Structural decisions

All four locked in earlier conversation.

### 1. Single entry point: "New report" → template gallery

The "New report" button in `ReportsFullView` no longer opens a blank
editor directly. It opens a `ReportTemplateGallery` modal. The
gallery has a prominent **Start blank** card alongside the four
template cards. Power users click "Start blank" once and get the
existing editor; new users see the templates first.

The empty state (no reports exist yet) inlines the same gallery
component so the templates are the first thing the user sees on a
fresh install, with no second click.

### 2. Templates as hardcoded TS constants

`src/lib/reportTemplates.ts` exports a typed array. No new endpoint,
no template-versioning question, no migration surface. Templates are
content the codebase owns and ships in releases.

```ts
export interface ReportTemplate {
  /// Stable slug, used as the template's identity for analytics
  /// (future) and as a React key in the gallery.
  id: string;
  /// One-line gallery card description.
  description: string;
  /// Lucide icon component.
  icon: LucideIcon;
  /// The CreateReportInput body to pre-fill the editor. `name` is
  /// editable; the user can rename before saving. Tag arrays stay
  /// empty — they're per-DB and the user picks at editor time.
  body: CreateReportInput;
}

export const REPORT_TEMPLATES: ReportTemplate[] = [
  { id: 'daily-briefing', ... },
  { id: 'weekly-contradictions', ... },
  { id: 'open-questions', ... },
  { id: 'monthly-themes', ... },
];
```

### 3. Four templates ship in v1

Each ships with a hand-written research prompt that gives the agent
enough structure to produce consistent output. The prompts are the
load-bearing content — the schedule and scope are easy, but the
prompt is what makes the template *good*.

#### Daily briefing

- **Schedule:** Daily 9am (`0 0 9 * * *`)
- **Source scope:** Since last run, all tags
- **Context scope:** Same as source
- **Citation policy:** Source only
- **Prompt sketch:**
  > Synthesize today's new atoms into a 2-3 paragraph briefing that
  > highlights what's noteworthy, what themes emerge, and where these
  > new notes connect to existing knowledge. Use [N] inline citations
  > to point at specific source atoms. Skip atoms that aren't
  > noteworthy. Write in the user's voice: concise, direct, mildly
  > analytical, no filler.

Duplicates the seeded briefing's intent, but lets users scope
additional briefings to specific tag subtrees ("Daily AI Briefing",
"Daily Politics Briefing"). The seeded report stays where it is; the
template is an additive starting point.

#### Weekly contradiction scan

- **Schedule:** Weekly Monday 9am (`0 0 9 * * 1`)
- **Source scope:** Since last run, all tags
- **Context scope:** Explicit, all tags, older-than-source window
- **Citation policy:** Source and context (must be able to cite the
  older claim, not just the new one)
- **Prompt sketch:**
  > For each atom captured this week, look for places where it
  > contradicts, complicates, or qualifies statements found in older
  > notes. For each contradiction:
  > - State the new claim with a [N] citation
  > - State the older claim it conflicts with, also cited
  > - Note whether this is a clean contradiction (direct logical
  >   conflict) or a tension (the new claim weakens or adds nuance to
  >   the older one)
  > If no contradictions exist this week, say so plainly and move on.

This is the highest-value template — contradiction detection is
exactly what the dual-scope + context-citable design was built for.
A user adopting this template is using the primitive's full capability.

#### Open questions status

- **Schedule:** Weekly Friday 4pm (`0 0 16 * * 5`)
- **Source scope:** Since last run
- **Context scope:** Same as source
- **Citation policy:** Source and context
- **Prompt sketch:**
  > Walk this week's new atoms. For each open question you find:
  > - Restate the question
  > - Cite the atom where it was raised
  > - Search the corpus for any answer or partial answer captured
  >   since the question was raised
  > - If you find an answer, cite it and mark "resolved" or "partially
  >   resolved"
  > - If not, mark "still open"
  > Group output by topic when natural. End with a list of the
  > longest-standing still-open questions.

#### Themes this month

- **Schedule:** Monthly, 1st 10am (`0 0 10 1 * *` — uses the Custom
  cron escape hatch since the preset chooser only models daily /
  weekdays / weekly / hourly)
- **Source scope:** Last 30 days
- **Context scope:** Same as source
- **Citation policy:** Source only
- **Prompt sketch:**
  > Synthesize the last 30 days of atoms into 3–5 themes. For each
  > theme:
  > - Name it in 3–5 words
  > - Describe the cluster of atoms it represents, with [N] citations
  > - Note whether this theme is new this month or continuing from
  >   prior coverage
  > - Call out the strongest individual atom (most-substantive or
  >   most-cited) for the theme
  > End with a "worth a deep dive" line picking the one theme you'd
  > recommend prioritizing.

### 4. Targeted polish

Three items, in this order:

**(a) Mobile collapse on ReportDetailView header.** Below `md`
(768px), the action cluster (Run Now, Edit, Delete) is too wide for
the row. Collapse to: keep Run Now as the visible primary button,
move Edit + Delete into a `⋮` overflow menu (`ContextMenu`
component). The status badge already moves to the meta band; we hide
the header copy of it on mobile (`hidden md:inline-flex`) so the
header row stays single-line.

**(b) Keyboard navigation on `FeaturedDropdown`.** When the menu
opens, focus the currently-featured option (or the first option if
nothing is featured). Arrow up/down moves selection; Enter activates;
Escape closes and returns focus to the trigger button. The menu role
+ `aria-activedescendant` model handles screen readers.

**(c) Keyboard navigation on `ContextMenu` (row overflow + new
mobile-header use).** Same pattern as the dropdown. The existing
component is mouse-only; extending it benefits both the row
overflow menu (4b) and the new mobile-header collapse from (a).

**(d) Empty-state copy refresh.** The current
`ReportsList` empty-state copy mentions "the next phase of authoring
lands the create flow" — phase-3-era language that's no longer true.
Replace with copy that points at the template gallery.

## Component breakdown

```
src/lib/reportTemplates.ts             # new — typed template constants
src/components/reports/
  ReportTemplateGallery.tsx            # new — modal with template cards + Start blank
  ReportTemplateCard.tsx               # new — one card in the gallery
  ReportsFullView.tsx                  # rewire "New report" button to gallery
  ReportsList.tsx                      # empty-state inline gallery + copy refresh
  ReportEditorModal.tsx                # accept optional `initialBody` prop for prefill
  ReportDetailView.tsx                 # mobile header collapse (action cluster → ⋮)
  FeaturedDropdown.tsx                 # keyboard navigation
src/components/ui/
  ContextMenu.tsx                      # keyboard navigation (benefits row overflow too)
```

## State management

No new store. Templates are stateless content. The flow:

1. User clicks "New report" → `ReportsFullView` opens
   `ReportTemplateGallery`
2. User clicks a template card → gallery closes,
   `ReportEditorModal` opens with `initialBody` set to the template's
   body
3. User clicks "Start blank" → gallery closes,
   `ReportEditorModal` opens with no `initialBody` (existing
   blank-create flow)
4. Editor save flows through the existing `useReportsStore.create`

The empty-state gallery in `ReportsList` uses the same
`ReportTemplateGallery` component inline (not modal), passing the
same click handlers.

## Edge cases

- **User picks a template, deletes everything, saves.** They get an
  empty report. That's their right; the editor's existing required-
  field validation (name + prompt non-empty) is the only floor.
- **Template references tags that don't exist in this DB.** v1
  templates ship with empty `*_tag_ids` arrays, so this can't
  happen. If we add tag-bearing templates later, the gallery card
  surfaces a "(this template uses tags you don't have)" hint and the
  editor opens with the missing tags shown but un-applied.
- **Monthly-themes Custom cron pasted into the editor.** The
  ScheduleField recognizes "Custom" only when the cron doesn't match
  any preset. Monthly schedules fall through to Custom automatically;
  the editor shows the raw cron with a 3-fire preview. Already works.
- **Mobile header overflow during a Run Now spinner.** The Run Now
  button label changes to "Running…" which is wider. We size the
  button with a `min-w` so the spinner state doesn't reflow the
  header — minor but worth catching.

## Phasing inside phase 5

Three commits, in order:

1. **Templates** — `reportTemplates.ts`, `ReportTemplateGallery`,
   `ReportTemplateCard`, `ReportEditorModal.initialBody`,
   `ReportsFullView` rewire, empty-state inline gallery + copy.
2. **Mobile header collapse** — `ReportDetailView` action cluster
   responsive behavior. Uses the existing `ContextMenu`.
3. **Keyboard nav** — `FeaturedDropdown` + `ContextMenu` arrow-key /
   Enter / Escape handling. Refocus the trigger on close.

Each is a self-contained commit; reviewer can read them
independently.

## Risks & mitigations

- **Template prompts age poorly.** The prompts ship as code; if a
  template starts producing bad output (e.g. an LLM provider drifts),
  iterating means an app release. *Mitigation:* the prompts are
  short, focused, and use citations as their main structural cue —
  the kind of prompt that should age well. If we need flexibility
  later, promoting to a backend endpoint is straightforward (the
  data shape is already a JSON-serializable struct).
- **First-run user picks "Daily briefing" template and creates a
  duplicate of the seeded report.** They end up with two reports
  firing daily. *Mitigation:* the gallery card description for Daily
  Briefing explicitly says "scope this to a specific topic — your
  database already has a general one." Plus the editor opens with
  the name pre-filled to "Daily Briefing" — most users will rename
  before saving.
- **ContextMenu keyboard nav regression in other call sites.** The
  component is used by the canvas right-click menu and tag tree;
  arrow-key behavior could conflict with their own focus. *Mitigation:*
  extend the component additively — focus management activates only
  when the menu is opened via keyboard (not via right-click), via a
  `triggerSource` prop or by detecting the focus state of the
  trigger element.

## Out of scope, queued for later (post-phase-5)

- **Orphan detection template.** Would need a semantic_search variant
  that returns "atoms with no nearby neighbors" — not currently
  expressible via the agent's tools. Add when the tool surface
  extends.
- **Task-run ledger view.** A "why did this report fail twice last
  week?" page on top of the `task_runs` table. Real work; defer
  until users ask.
- **Bulk actions across reports.** Not needed at small N.
- **Per-report retry-attempt configuration.** Backend supports it;
  defer the UI until someone needs it.
- **Citation popover on FindingRow.** A hover popover showing
  cited-atom excerpts directly in the findings list, matching what
  wiki articles do. Nice-to-have polish.
- **Full a11y audit + screen-reader pass on every reports screen.**
  The phase-5 polish targets the worst offender; a complete pass
  waits until the feature is in front of users who need it.
- **Backend template catalog endpoint.** Promote templates from TS
  constants to backend data if/when shipping new templates without
  app updates matters.
