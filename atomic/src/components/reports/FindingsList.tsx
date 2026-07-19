import { memo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { FileText } from 'lucide-react';
import { ReportFindingWithAtom } from '../../stores/reports';
import { FindingRow } from './FindingRow';

interface FindingsListProps {
  findings: ReportFindingWithAtom[] | undefined;
  isLoading: boolean;
  onFindingClick: (atomId: string) => void;
}

const ROW_HEIGHT = 56;

/// Virtualized findings list for the report detail view. Most-recent
/// first (the order the wire response gives us). Empty state explains
/// that findings land here when the report runs.
///
/// `findings === undefined` means we haven't fetched yet; the skeleton
/// state below covers it. `[]` after a fetch means truly empty.
export const FindingsList = memo(function FindingsList({
  findings, isLoading, onFindingClick,
}: FindingsListProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const items = findings ?? [];

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 6,
  });

  if (findings === undefined || isLoading) {
    return (
      <div className="h-full overflow-y-auto scrollbar-auto-hide">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="grid grid-cols-[88px_1fr_auto] items-center gap-4 px-5 py-3 border-b border-[var(--color-border)]">
            <div className="h-3 w-12 bg-[var(--color-border)]/60 rounded animate-pulse" />
            <div className="h-3.5 w-3/4 bg-[var(--color-border)] rounded animate-pulse" />
            <div className="h-3 w-8 bg-[var(--color-border)]/40 rounded animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <FileText className="w-12 h-12 text-[var(--color-border)] mb-3" strokeWidth={1.5} />
        <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-1">No findings yet</h3>
        <p className="text-[13px] text-[var(--color-text-secondary)] max-w-sm leading-relaxed">
          When this report runs — on its schedule or via Run now — each
          finding lands here as an atom in your knowledge base.
        </p>
      </div>
    );
  }

  return (
    <div ref={parentRef} className="h-full overflow-y-auto scrollbar-auto-hide">
      <div className="relative w-full" style={{ height: `${virtualizer.getTotalSize()}px` }}>
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const item = items[virtualRow.index];
          return (
            <div
              key={item.finding.finding_atom_id}
              className="absolute left-0 right-0"
              style={{
                top: `${virtualRow.start}px`,
                height: `${virtualRow.size}px`,
              }}
            >
              <FindingRow item={item} onClick={onFindingClick} />
            </div>
          );
        })}
      </div>
    </div>
  );
});
