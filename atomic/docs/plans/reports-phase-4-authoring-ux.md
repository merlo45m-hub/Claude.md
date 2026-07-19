# Reports Phase 4 — Authoring UX

Backend primitive is done (phases 1, 1.5, 2, 3). Atoms carry a `kind`
discriminator, the execution ledger runs scheduled tasks with claim/lease/
backoff, the reports primitive owns the run lifecycle end-to-end, and the
daily briefing has been collapsed into the seeded "Daily Briefing" report.
The dashboard widget already reads from the per-DB `featured_report_id`.

What's missing is the React surface that lets users **see, author, run,
and manage** arbitrary reports — not just the seeded one. Phase 4 ships
that surface.

## Goals

- A first-class place in the app where reports live, distinct from
  atoms, wikis, tags, settings.
- Create / edit / enable-disable / delete arbitrary reports through a
  focused form, without writing cron by hand.
- Manual "run now" with live feedback and clear failure surfacing.
- Per-report findings history with citations, navigable to the
  underlying atoms.
- A way to promote any report to the dashboard widget — not just the
  seeded Daily Briefing.

## Non-goals (v1)

- Curated templates (phase 5).
- Per-report retry-attempt configuration (the ledger uses the 3-attempt
  default; phase 4 doesn't expose it).
- A "compare two findings" diff view.
- Mobile-first redesign. Mobile gets the same view via responsive
  collapse, but tablet/desktop is the design target.

## Structural decisions

These four set the shape of the whole feature. All four are confirmed.

### 1. New top-nav mode `reports`

`useUIStore.viewMode` gains a fifth value — `'reports'` — and `MainView`'s
pill loop (the one that shares the `LayoutGroup` blob with open atom
tabs) gets a new entry. Telescope icon (Lucide `Telescope`) reads
"research / lookout" without colliding with any existing meaning.

Reports are content the user navigates to, not configuration. Burying
them in a Settings tab would have hidden the most interesting feature
in the app behind a gear icon. The fifth pill mirrors how wiki was
introduced.

### 2. Editor in a Modal

Create + edit reuse a single `ReportEditorModal`, modeled after
`NewWikiModal`. The right drawer is reserved for chat; modal keeps the
authoring surface focused and dismissible without competing with the
list behind it.

### 3. Dedicated detail view per report

Clicking a row pushes a `ReportDetailView` into the main area —
takeover pattern matching how `AtomReader` overlays `MainView`'s default
content. The detail view hosts: full findings history (most recent
first, virtualized), the inline-edit form (same shape as the modal but
collapsed), a Run-Now button with live state, a "Feature on dashboard"
toggle, and the delete affordance.

### 4. Featured-report picker as inline dropdown in widget eyebrow

The existing `BriefingWidget` eyebrow row ("BRIEFING · MAY 23") gains a
chevron when more than one report exists. Clicking opens a menu of
reports; selecting one calls `set_featured_report_id` and the widget
refetches. Discoverable, in-context — users never have to leave the
dashboard to swap their featured report.

## Visual identity

Atomic's design system stays put — dark Obsidian-inspired, purple
accent, user-selectable body font via `data-font`. Imposing a serif on
report names would fight the user's chosen typography. The Reports
identity comes from **scale, rhythm, and restraint**:

- **Slim wide rows, not square cards.** Wikis use square cards; reports
  earn visual separation by using a different list geometry. Each row
  is a horizontal band with three columns: identity (name + last
  finding excerpt), schedule strip + cron, status badge + actions.
- **Mono for schedules.** Cron expressions and "Next: Tue 8:00 AM"
  render in `var(--font-mono)`. Reinforces the "machine-scheduled"
  identity using a font Atomic already loads.
- **Eyebrow uppercase status labels.** `ACTIVE`, `PAUSED`, `RUNNING NOW`,
  `FAILED · 2H AGO` — same `text-[11px] uppercase tracking-[0.14em]`
  treatment the existing `BriefingWidget` uses. Tabular figures for
  relative times.
- **Schedule strip — next 7 days.** A 7-cell horizontal grid per row,
  one cell per upcoming day, filled where the report will fire.
  Computed client-side from the cron + tz. Density-at-a-glance without
  reading cron.
- **Run-state pulse.** When a report's ledger row is `running`, the
  row gets a 1px purple border and a slow opacity pulse (CSS
  animation). The row itself is the indicator — no spinner glyph.
- **Last finding excerpt** as the tertiary line. First ~80 chars of the
  most recent finding atom's content, italic muted. Turns each row
  into a self-evident "this is what this report produces."
- **Purple accent reserved.** Only used for: Featured badge, run-state
  pulse, primary action buttons. The rest of the chrome stays in the
  neutral panel/border palette.

## Component breakdown

```
src/components/reports/
  index.ts
  ReportsFullView.tsx        # mounted by MainView when viewMode === 'reports'
  ReportsList.tsx            # virtualized list — @tanstack/react-virtual
  ReportRow.tsx              # one report — schedule strip, status, actions
  ReportDetailView.tsx       # findings history + inline editor + run-now
  ReportEditorModal.tsx      # create / edit form
  ReportEmptyState.tsx       # "no reports yet" — phase-5 templates land here
  ScheduleField.tsx          # cron + tz editor (revive briefing logic)
  ScheduleStrip.tsx          # 7-day next-fire visualization
  ScopeField.tsx             # source/context scope: tags + window + kinds
  CitationPolicyField.tsx    # radio: source-only | context-citable
  FindingsList.tsx           # most-recent-first findings with citation count
  StatusBadge.tsx            # eyebrow label component
src/stores/reports.ts        # Zustand store
```

## State management

A single `useReportsStore` parallels `useWikiStore`:

```ts
{
  reports: Report[];
  byId: Record<string, Report>;
  findingsByReport: Record<string, ReportFindingWithAtom[]>;
  citationsByAtom: Record<string, ReportFindingCitation[]>;
  isLoadingList: boolean;
  runningReportIds: Set<string>;   // optimistic on click Run Now
  fetchAll(): Promise<void>;
  create(req): Promise<Report>;
  update(id, req): Promise<Report>;
  setEnabled(id, enabled): Promise<void>;
  delete(id): Promise<void>;
  runNow(id): Promise<void>;
  fetchFindings(id): Promise<void>;
  fetchCitations(atomId): Promise<void>;
  reset(): void;
}
```

**Real-time refresh.** Subscribe to `atom-created`, filter on
`payload.kind === 'report'`, and re-fetch `findingsByReport[reportId]`
for any loaded report when a finding lands. (Same shape
`BriefingWidget` uses today — payload is `AtomWithTags` which
`#[serde(flatten)]`s the inner atom, so `kind` is at the top level.)

**Run-state refresh.** A finding atom landing implicitly means the run
finished successfully; for failures we re-fetch the report itself
(carries `last_error`) on a 30s tick while a detail view is open and a
report is in the local `runningReportIds` set. Phase 4 doesn't
introduce a new event type for run-state — the existing AtomCreated +
report-cache polling cover both terminal states.

## Routing & state plumbing

- Add `'reports'` to `useUIStore`'s `ViewMode` union.
- Add `reportsDetailState: { reportId: string | null }` to `useUIStore`
  (parallels `readerState` / `wikiReaderState`). `openReportDetail(id)`
  and `closeReportDetail()` actions.
- `MainView.tsx` content switch: if `reportsDetailState.reportId` is
  set, render `ReportDetailView`; else if `viewMode === 'reports'`,
  render `ReportsFullView`.
- Pill rendering in `MainView.tsx` lines 263–294 gets a fifth entry:
  `['reports', Telescope, 'Reports']`.

## Editor form fields

The modal and the inline detail-view editor share a single field-by-
field implementation; only the chrome differs. Fields:

| Field | Control | Notes |
|---|---|---|
| Name | text input | required, 1–80 chars |
| Prompt | textarea | required, monospace; the "what is this report supposed to do" |
| Schedule | `ScheduleField` | cron + tz, with a friendly preset selector ("Every weekday 8am") and a "Custom cron" escape hatch |
| Enabled | toggle | mirrors `set_report_enabled` — saved independently of other edits |
| Source scope | `ScopeField` | tags (multi-select), window (Since-last-run / Last 24h / Last 7d / All-time), kinds (default Captured) |
| Context scope | `ScopeField` | same shape; defaults to "same as source" with an "override" expander |
| Citation policy | radio | "Cite source atoms only" (default) / "Allow citing context atoms" |
| Output tags | tag multi-select | tags applied to the finding atom; defaults to the seeded "Reports" tag |

`ScheduleField` revives the cron/tz UX that lived under the old briefing
settings before phase 3 deleted it. The cron logic itself (`cronParser`,
the next-fire preview) survived the collapse — phase 4 just rebuilds
the shell.

## Edge cases handled in v1

- **No featured report set, multiple reports exist.** Dashboard widget
  shows a "Pick a featured report ▾" inline prompt rather than the bare
  empty state.
- **Featured report deleted while the widget is open.** Backend already
  clears the pointer in `delete_report`. Widget re-reads on focus and
  on a new event `dashboard-featured-changed` (new — small server-side
  broadcast on featured-report writes).
- **Editing schedule of a currently-running report.** Save goes through
  but a tooltip notes "Current run continues; new schedule applies
  after it finishes."
- **Deleting a report with findings.** Confirm dialog: "Findings will
  remain in your atoms (kind=report). Only the schedule and report
  definition will be deleted." Findings outlive their producer by
  design.
- **Run Now while ledger says another worker holds the lease.** Backend
  returns `RunOutcome::Skipped` — the UI surfaces a toast: "Already
  running" and leaves the optimistic `runningReportIds` entry until
  the row's cache updates.
- **Backend validation failure on save.** Modal stays open; field-level
  error inlined under the offending control (schedule = invalid cron /
  timezone; name = empty / too long).

## Phasing inside phase 4

Sub-PRs to keep review tractable:

- **4a — read-only.** `useReportsStore` skeleton (fetch only),
  `ReportsFullView`, `ReportsList`, `ReportRow`, `ScheduleStrip`,
  `StatusBadge`. New top-nav mode lights up. No editor, no actions.
- **4b — write.** `ReportEditorModal`, `ScheduleField`, `ScopeField`,
  `CitationPolicyField`. Create + edit + enable/disable + delete.
- **4c — detail + run-now.** `ReportDetailView`, `FindingsList`,
  optimistic `runningReportIds`, the featured-report dropdown in
  `BriefingWidget`'s eyebrow, the `dashboard-featured-changed` event
  (small server-side addition + handler).
- **4d — polish.** Empty state copy + the template-slot hooks phase 5
  will fill, mobile responsive pass, accessibility audit
  (keyboard navigation, focus management on modal close), edge-case
  toasts.

## Risks & mitigations

- **Form complexity.** Source + context + citation policy + tags is a
  lot for one modal. *Mitigation:* the modal opens with the four most
  common fields visible (name, prompt, schedule, enabled) and an
  "Advanced" expander reveals scopes + citation + output tags.
  Defaults are sensible enough that the common case is a 4-field form.
- **Cron is intimidating.** *Mitigation:* the preset selector covers
  ~90% of real schedules ("Every weekday 8am", "Daily at HH:MM",
  "Every Monday 9am", "Hourly", "Custom"). The cron string itself is
  shown read-only beneath the preset, and the "Custom" option
  unlocks a raw cron input with live validation + next-3-fires
  preview.
- **Run-state churn.** Polling every 30s for failed runs is wasteful at
  scale. *Mitigation:* polling only happens when the detail view is
  open AND the report is in `runningReportIds`. Idle list view does
  zero polling — it relies on `atom-created` events for refresh.
- **Mobile cramping.** The slim-wide-row geometry is built for ≥640px
  viewports. *Mitigation:* below the `md` breakpoint, rows collapse to
  vertical stacks (identity / schedule strip on one row, status +
  actions on the next), and the detail view's inline editor switches
  to a full-screen sheet instead of side-by-side.

## Out of scope, queued for later

- **Curated templates** (phase 5). `ReportEmptyState.tsx` will have
  empty slots where phase 5 drops in template chips ("Weekly
  contradiction scan", "Open questions status", etc.).
- **Bulk actions** (enable all / disable all / re-run all). Defer until
  we have a user with >10 reports.
- **Run history beyond findings.** The `task_runs` ledger has rich
  retry history; phase 4 surfaces only the terminal-success findings.
  A "Run history" sub-tab on the detail view is a phase-5+ addition
  if users ask for it.
