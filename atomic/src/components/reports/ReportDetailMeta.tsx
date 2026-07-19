import { memo, useMemo } from 'react';
import { Report } from '../../stores/reports';
import { useTagsStore, TagWithCount } from '../../stores/tags';
import { ScheduleStrip } from './ScheduleStrip';

interface ReportDetailMetaProps {
  report: Report;
}

/// Flatten the hierarchical tags tree into a lookup map. Used to
/// resolve tag names for the scope summary without re-walking the
/// tree on every render.
function flattenTags(nodes: TagWithCount[]): Map<string, string> {
  const map = new Map<string, string>();
  function walk(ns: TagWithCount[]) {
    for (const n of ns) {
      map.set(n.id, n.name);
      if (n.children) walk(n.children);
    }
  }
  walk(nodes);
  return map;
}

function describeDuration(value: string): string {
  switch (value) {
    case 'PT24H': return 'Last 24 hours';
    case 'P7D': return 'Last 7 days';
    case 'P30D': return 'Last 30 days';
    default: return value;
  }
}

function describeWindow(w: Report['source_scope_window']): string {
  if (w === null) return 'All time';
  if (w === 'since_last_run') return 'Since last run';
  return describeDuration(w.duration);
}

function describeContextWindow(w: Report['context_scope_window']): string {
  if (w === null) return 'All time';
  if (w === 'older_than_source') return 'Older than source';
  return describeDuration(w.duration);
}

function describeContextMode(report: Report): string {
  switch (report.context_scope_mode) {
    case 'same_as_source': return 'Same as source';
    case 'all': return 'All atoms';
    case 'explicit':
      if (report.context_scope_tag_ids.length === 0) return 'No context';
      return `${report.context_scope_tag_ids.length} tag${report.context_scope_tag_ids.length === 1 ? '' : 's'}`;
  }
}

/// Meta band rendered just below the detail-view header. Schedule
/// strip + cron + tz on the left, scope summary on the right (or
/// stacked on mobile).
export const ReportDetailMeta = memo(function ReportDetailMeta({ report }: ReportDetailMetaProps) {
  const tags = useTagsStore(s => s.tags);
  const tagMap = useMemo(() => flattenTags(tags), [tags]);

  // Source tags: show names if ≤ 2, count otherwise. Avoids a wide
  // line for reports scoped to many tags.
  const sourceTags = useMemo(() => {
    if (report.source_scope_tag_ids.length === 0) return 'All tags';
    if (report.source_scope_tag_ids.length <= 2) {
      return report.source_scope_tag_ids
        .map(id => tagMap.get(id) ?? id)
        .join(', ');
    }
    return `${report.source_scope_tag_ids.length} tags`;
  }, [report.source_scope_tag_ids, tagMap]);

  const sourceWindowLabel = describeWindow(report.source_scope_window);
  const contextModeLabel = describeContextMode(report);
  const contextWindowLabel = report.context_scope_mode === 'same_as_source'
    ? null
    : describeContextWindow(report.context_scope_window);
  const citationLabel =
    report.citation_policy === 'source_only'
      ? 'Cite source only'
      : 'Cite source + context';

  return (
    <div className="
      flex flex-col md:flex-row md:items-start md:justify-between gap-3
      px-5 py-3 border-b border-[var(--color-border)] flex-shrink-0
      bg-[var(--color-bg-card)]/30
    ">
      {/* Schedule */}
      <div className="flex items-center gap-3 min-w-0">
        <ScheduleStrip
          cron={report.schedule}
          tz={report.schedule_tz}
          muted={!report.enabled}
        />
        <div className="flex flex-col leading-tight">
          <code className="font-mono text-[11px] text-[var(--color-text-secondary)] tabular-nums">
            {report.schedule}
          </code>
          {report.schedule_tz && (
            <span className="font-mono text-[10px] text-[var(--color-text-tertiary)]">
              {report.schedule_tz}
            </span>
          )}
        </div>
      </div>

      {/* Scope summary — terse, comma-separated. */}
      <div className="text-[12px] text-[var(--color-text-secondary)] tabular-nums">
        <span className="text-[var(--color-text-tertiary)] uppercase tracking-[0.1em] text-[10.5px] mr-1.5">
          Source
        </span>
        {sourceTags}
        <span className="text-[var(--color-text-tertiary)] mx-1.5">·</span>
        {sourceWindowLabel}
        <span className="text-[var(--color-text-tertiary)] mx-1.5">·</span>
        <span className="text-[var(--color-text-tertiary)] uppercase tracking-[0.1em] text-[10.5px] mr-1.5">
          Ctx
        </span>
        {contextModeLabel}
        {contextWindowLabel && (
          <>
            <span className="text-[var(--color-text-tertiary)] mx-1.5">·</span>
            {contextWindowLabel}
          </>
        )}
        <span className="text-[var(--color-text-tertiary)] mx-1.5">·</span>
        {citationLabel}
      </div>
    </div>
  );
});
