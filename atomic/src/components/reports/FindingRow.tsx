import { memo, useEffect, useMemo } from 'react';
import { Quote } from 'lucide-react';
import { ReportFindingWithAtom, useReportsStore } from '../../stores/reports';
import { formatRelativeDate } from '../../lib/date';

interface FindingRowProps {
  item: ReportFindingWithAtom;
  onClick: (atomId: string) => void;
}

/// One row in the FindingsList. Layout: eyebrow date column, single-
/// line content excerpt, citation count badge on the right.
///
/// Citation count loads lazily — the row mounts an effect that calls
/// `fetchCitationCount`, which is idempotent and caches by atomId.
/// Cheaper than fetching counts for the whole list up front, since the
/// virtualizer only renders rows in view + a small overscan window.
export const FindingRow = memo(function FindingRow({ item, onClick }: FindingRowProps) {
  const count = useReportsStore(s => s.citationCountsByAtomId[item.atom.id]);
  const fetchCitationCount = useReportsStore(s => s.fetchCitationCount);

  useEffect(() => {
    fetchCitationCount(item.atom.id);
  }, [fetchCitationCount, item.atom.id]);

  // Extract the first non-empty line as the row title. Markdown atoms
  // may start with `# Heading` or a paragraph; either way we strip
  // markers and trim. Capped at 110 chars for the slim row.
  const title = useMemo(() => {
    const lines = item.atom.content.split('\n');
    for (const raw of lines) {
      const cleaned = raw.replace(/^#+\s*/, '').trim();
      if (cleaned.length > 0) {
        return cleaned.length > 110 ? cleaned.slice(0, 109) + '…' : cleaned;
      }
    }
    return '(empty finding)';
  }, [item.atom.content]);

  return (
    <button
      type="button"
      onClick={() => onClick(item.atom.id)}
      className="
        w-full grid grid-cols-[88px_1fr_auto] items-center gap-4 px-5 py-3
        border-b border-[var(--color-border)]
        text-left cursor-pointer
        hover:bg-[var(--color-bg-hover)] transition-colors
      "
    >
      <span className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-tertiary)] tabular-nums">
        {formatRelativeDate(item.atom.created_at).toUpperCase()}
      </span>

      <span className="text-[14px] text-[var(--color-text-primary)] truncate">
        {title}
      </span>

      <span
        className={`
          inline-flex items-center gap-1 text-[11px] tabular-nums
          ${count && count > 0 ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-tertiary)]/50'}
        `}
        title={count !== undefined ? `${count} citation${count === 1 ? '' : 's'}` : 'Loading citations…'}
      >
        <Quote className="w-3 h-3" strokeWidth={2} />
        {count !== undefined ? count : '—'}
      </span>
    </button>
  );
});
