# Reports Phase 4c — Detail View, Run-Now, Featured Picker

4a shipped the read-only reports list. 4b shipped create / edit /
enable-disable / delete via a modal. 4c adds the substantive
"this is what a report **is**" surface — a dedicated detail view per
report, manual execution with live state feedback, and the
dashboard's featured-report selector.

After 4c, every backend capability of the reports primitive has a UI
home. 4d is polish (empty-state copy, mobile pass, a11y, edge-case
toasts).

## Goals

- A canonical place to see a single report's full state: schedule,
  scope, citation policy, findings history, error history.
- Manual "Run now" with live feedback. The button disables while the
  run is in flight; AtomCreated clears the running state; the failure
  path (no event) is caught by a per-report poll while the detail
  view is open.
- A featured-report picker that lets any report — not just the seeded
  Daily Briefing — fill the dashboard widget's slot.
- Cross-window consistency: the dashboard widget reacts when another
  client changes the featured report, via a new
  `dashboard-featured-changed` broadcast.

## Non-goals (v1)

- Inline-edit form on the detail view. Editing goes through the
  same `ReportEditorModal` introduced in 4b. One canonical editor
  surface; no duplicated field code.
- "Run again on completion" queueing. Run-Now is disabled while
  running. Phase 5 may add queueing if users ask.
- A separate "Run history" view showing the `task_runs` ledger
  (attempts, backoff, etc.). The findings list is the user-facing
  history; ledger detail stays an internal concept.
- Bulk featured-report behavior (e.g. multiple featured at once).
  Backend's per-DB pointer is a single id; UI follows.

## Structural decisions

All four locked in earlier conversation.

### 1. URL: `/reports/:id`

Detail view is URL-addressable. `ParseLocation` gains a new variant
`{ kind: 'reports-detail'; reportId: string }`. `viewPath` and
friends grow a `reportDetailPath(reportId)` helper. Mirrors how
`AtomReader` works via `/atoms/:id` — deep links survive refreshes,
browser back/forward navigate naturally, no separate URL scheme to
explain.

`useUIStore` gains:
```ts
reportsDetailState: { reportId: string | null }
openReportDetail(reportId: string): void
closeReportDetail(): void
```

`MainView`'s content switch adds a branch: if `reportsDetailState.reportId`
is set, render `ReportDetailView`; else if `viewMode === 'reports'`,
render `ReportsFullView`.

### 2. Modal-only edit surface

The detail view does *not* host an inline edit form. An "Edit"
affordance in the header opens the existing `ReportEditorModal` with
the active report. Pros: zero duplication, single source of truth for
field validation, modal already handles minimal-patch updates.

The header carries a compact read-only summary of schedule + scope
that gives users enough context not to need the editor open most of
the time.

### 3. Stacked layout (meta band + findings)

The detail view is one scroll axis. From top to bottom:

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back   Report Name ★      [Run Now] [Edit] [⋮ Delete]    │  header
├─────────────────────────────────────────────────────────────┤
│  STATUS · LAST RUN 2H AGO          schedule strip · cron    │  meta band
│  Scope: tagA, tagB · last 7 days · cite source only         │
├─────────────────────────────────────────────────────────────┤
│  FINDINGS                                                   │
│  ──────────────────────────────────────                     │
│  MAY 23  ✦ Today's AI coverage skews toward                  │
│         agentic frameworks                          [4 cites] │
│  ──────────────────────────────────────                     │
│  MAY 22  ✦ ...                                              │
│         ...                                                 │
└─────────────────────────────────────────────────────────────┘
```

Findings list takes the remaining vertical space; virtualized via
`@tanstack/react-virtual` so 365 daily findings render instantly.

Mobile collapse: the actions row stacks under the title; the meta
band wraps; findings stay full-width.

### 4. Star toggle for "Feature on dashboard"

A filled-star icon to the right of the report name. Filled = this
report is currently featured. Click toggles via
`set_featured_report_id` (setting to `null` clears; setting to this
id features). Tooltip: "Feature on dashboard" / "Unfeature".

Star pattern reads as "favorite" universally and doesn't add chrome
the way a labeled switch would. Discoverability is fine because the
star is the second visual element in the header next to the name.

## Run-Now lifecycle

Manual execution has four observable states:

1. **Idle** — button labeled "Run now", enabled. Click → 2.
2. **Dispatching** — POST `/api/reports/:id/run` in flight. Button
   shows a small spinner; brief, sub-second.
3. **Running** — server returned 202; reportId added to
   `runningReportIds` set. Button labeled "Running…", disabled.
   ScheduleStrip row gains the purple pulse it shows for any
   running report.
4. **Done** — `atom-created` event with `kind === 'report'` for an
   atom whose `last_finding_atom_id` matches: refetch findings,
   remove from `runningReportIds`. Toast: "New finding".

**Failure path.** A failed run does not broadcast `atom-created` —
only success does. The report cache's `last_error` field gets set
server-side. While the detail view is open *and* a report is in
`runningReportIds`, we poll `get_report(id)` every 30s. If the
returned row has `last_error` set + `last_run_at` after the
dispatch time, the run finished as a failure: remove from running,
toast the error, render the new `FAILED` status badge.

**Stale-running guard.** If a Run-Now is dispatched and neither
event nor poll resolves within 5 minutes, the optimistic running
state clears with a "Couldn't confirm completion — refresh to check"
toast. This is belt-and-suspenders for browser sleep / WebSocket
hiccups; in normal operation the event resolves in seconds.

**Contention.** Run-Now is disabled while the report is in
`runningReportIds`. If the backend nonetheless returns `Skipped`
(another worker grabbed the lease, e.g. a scheduled tick during a
manual dispatch), we surface a "Already running" toast and add the
id to `runningReportIds` based on the report's current cache
fields. Belt-and-suspenders for the same reason as above.

## Findings list

`FindingsList` is a virtualized list with this row shape:

```
DATE     ✦ first-line of finding content, truncated to one line     [N cites]
```

- `DATE` is `formatRelativeDate(finding.created_at).toUpperCase()`
  in the small eyebrow style — `2H AGO`, `MAY 22`, etc.
- The first-line content is `finding_atom.content.split('\n')[0]`
  trimmed and ellipsized. We're not loading full atom prose for
  every row — the cheap signal is the title.
- Citation count comes from a `citations.length` join on the
  findings query response. Alternative: hand-roll a new endpoint
  that returns `(ReportFinding, AtomWithTags, citation_count)`.
  v1 issues N+1 by calling `list_finding_citations` lazily for each
  rendered row; phase 5 can promote it to a join if performance
  surfaces. (Backend has the data; this is just N small joins.)
- Click → opens the standard `AtomReader` for the finding atom.
  Standard atom view shows the citations inline via the existing
  `CitationLink` component — already wired in phase 3 for the
  dashboard widget.

Pagination: 50 findings per page, "Load more" button at the end —
matches how the atoms list paginates (`hasMore` flag from the
store).

## Featured-report picker

Two entry points share one store + one event:

### `BriefingWidget` eyebrow dropdown

The widget's existing eyebrow row (`BRIEFING · MAY 23 ▾`) becomes
clickable when more than one report exists. Click opens a popover
menu:

```
┌─────────────────────────┐
│  ✓ Daily Briefing       │
│    Weekly contradiction │
│    Open questions       │
│  ─────────────────────  │
│    Unfeature            │
└─────────────────────────┘
```

Selecting a report calls `set_featured_report_id(reportId)` and the
widget refetches. "Unfeature" calls it with `null`.

### Star toggle in `ReportDetailView`

Documented above. Same store mutation, same effect.

### Cross-window sync

A new server-side event `dashboard-featured-changed` broadcasts
on every `set_featured_report_id` write. Payload: `{ report_id: string | null }`.
Both the widget and the detail view subscribe and refetch on receipt.

Tiny addition server-side:
- `routes/dashboard.rs::set_featured_report` emits the event after
  the successful write
- New `ServerEvent::DashboardFeaturedChanged { report_id: Option<String> }`
  variant on the broadcast channel
- WS bridge passes it through to subscribers

## Component breakdown

```
src/components/reports/
  ReportDetailView.tsx          # new — orchestrates everything below
  ReportDetailHeader.tsx        # name + star + actions row
  ReportDetailMeta.tsx          # status + schedule + scope summary
  FindingsList.tsx              # virtualized list of finding rows
  FindingRow.tsx                # one row, opens AtomReader on click
  FeaturedStarButton.tsx        # the filled-star toggle
  FeaturedDropdown.tsx          # the picker for BriefingWidget eyebrow
src/components/dashboard/widgets/
  BriefingWidget.tsx            # extend eyebrow with FeaturedDropdown
src/stores/reports.ts           # extend with runningReportIds + findings
src/stores/featuredReport.ts    # add cross-window event handling
src/stores/ui.ts                # reportsDetailState
src/router/routes.ts            # /reports/:id parsing
```

## State management

`useReportsStore` extensions:

```ts
{
  // existing 4b state...
  runningReportIds: Set<string>;
  // findings + citations cached at the detail-view level. Stored
  // keyed by reportId, not jammed onto a single 'activeReport' so
  // navigating between detail views doesn't flicker.
  findingsByReport: Record<string, ReportFindingWithAtom[]>;
  citationCountsByAtomId: Record<string, number>;
  // actions
  fetchFindings(reportId: string, limit?: number): Promise<void>;
  fetchCitationCount(atomId: string): Promise<void>;
  runNow(reportId: string): Promise<void>;
  // Internal: invoked by AtomCreated subscription and the 30s poll.
  markRunComplete(reportId: string, outcome: 'success' | 'failure'): void;
}
```

`useFeaturedReportStore` extensions:

```ts
{
  // existing state...
  setFeatured(reportId: string | null): Promise<void>;
  // The atom-created subscription stays as-is. Add a parallel
  // subscription to `dashboard-featured-changed` that just calls
  // `fetchLatest()`.
}
```

## URL plumbing

`routes.ts`:

```ts
export type ParsedRoute =
  | ...
  | { kind: 'reports-detail'; reportId: string };

const VIEW_MODES: ViewMode[] = ['dashboard', 'atoms', 'canvas', 'wiki', 'reports'];

export function reportDetailPath(reportId: string): string {
  return `/reports/${encodeURIComponent(reportId)}`;
}

// parseLocation: match /reports/<id> before falling through to view
// mode check (since 'reports' is also a base view mode).
const reportMatch = path.match(/^\/reports\/([^/]+)$/);
if (reportMatch) {
  return { kind: 'reports-detail', reportId: decodeURIComponent(reportMatch[1]) };
}
```

Route hook in App.tsx (or wherever ParsedRoute is dispatched) maps
`reports-detail` to `useUIStore.openReportDetail(reportId)` and sets
`viewMode = 'reports'` so the top-nav pill stays highlighted.

## Edge cases handled in v1

- **Report deleted while its detail view is open** — store's `delete`
  removes the row from `reports` and `byId`. Detail view detects the
  missing entry on next render and dispatches `closeReportDetail()`
  with a toast: "Report was deleted".
- **Featured pointer cleared by backend on delete** — the new
  `dashboard-featured-changed` event fires with `report_id: null`;
  widget refetches and shows its empty/no-featured state.
- **Cross-window edit** — clicking Edit in window A while window B
  is on the same detail view: window B's report row updates via the
  existing list refetch on focus (added in 4a) plus the optimistic
  update from the editor save. No new event needed; the change is
  already visible next time window B reads `byId[reportId]`.
- **Run-Now while detail view is closing** — `runNow` resolves into
  the store regardless of whether the detail view is mounted. The
  AtomCreated subscription lives at the store level (set up in
  `fetchAll`), so the running state clears properly even if the user
  navigated away.
- **AtomCreated lands for a finding we don't have a report-row
  cached for** — happens if a scheduled run completes for a report
  whose row hasn't been fetched. Currently the dashboard
  `BriefingWidget` handles this via its own `featuredReport` store;
  the detail view will do the same — if `runningReportIds` doesn't
  contain the report id, the event is a no-op for the detail view.

## Phasing inside 4c

Execution order (single PR; commits can be split for review):

1. **URL + routing** — add `reportDetailPath`, the new `ParsedRoute`
   variant, parser, and ui-store state. `MainView` content switch.
   Skeleton `ReportDetailView` that just shows the report's name +
   back button.
2. **Findings list** — `FindingsList`, `FindingRow`, store extensions
   for `findingsByReport`. Wire row click to existing `openReader`.
3. **Run-Now lifecycle** — `runningReportIds`, the dispatch action,
   `atom-created` integration (re-use existing subscription —
   broaden the filter to also clear running state, not just refresh
   findings), the 30s failure poll, the 5min stale guard.
4. **Featured picker** — `FeaturedStarButton`, `FeaturedDropdown`,
   `useFeaturedReportStore.setFeatured`. Backend event
   (`dashboard-featured-changed`) — `ServerEvent` variant + emit on
   write + WS bridge. Both subscribers wire up.
5. **Header + meta band + edit handoff** — fold everything into the
   final layout, wire the Edit button to `ReportEditorModal`.

## Risks & mitigations

- **N+1 citation count requests on first paint of findings list.**
  *Mitigation:* lazy fetch as rows scroll into view via the
  virtualizer's `getVirtualItems()` overscan window. Cache hit on
  subsequent renders. If perf surfaces in real use, a join endpoint
  is a phase-5 polish item.
- **Poll spam when many reports are running simultaneously.** Today
  there's no UI way to dispatch multiple Run-Nows fast; ScheduledRun
  collisions also won't show up because they all bypass the detail
  view's poll. *Mitigation:* poll is gated to "detail view open AND
  in runningReportIds", so it's effectively at most one report at
  any time.
- **Star toggle race with the dropdown.** User stars from the detail
  view; another window's dropdown sees a stale "current id" until
  the event lands. *Mitigation:* the `dashboard-featured-changed`
  event resolves it within 100ms. The optimistic update on the
  toggling client makes it feel instant locally.
- **Detail view freezes on a report with thousands of findings.**
  *Mitigation:* virtualized list with a 50-row initial page + lazy
  load. The findings query is already paginated.

## Out of scope, queued for later

- **Task-run ledger view** (attempt history, backoff timing).
  Phase 5 if users ask for it.
- **Citation popover on finding rows.** Today citations show when
  the user opens the underlying atom in AtomReader. A hover popover
  on a finding row (preview of the cited atom) is a polish item.
- **Bulk actions across reports** from the detail view ("re-run all
  enabled"). Phase 5.
- **Per-report retry-attempt configuration.** The backend has the
  knob; the editor doesn't surface it. Defer to phase 5.
