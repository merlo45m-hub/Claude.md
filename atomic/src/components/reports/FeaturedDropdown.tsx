import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Telescope } from 'lucide-react';
import { useReportsStore } from '../../stores/reports';
import { useFeaturedReportStore } from '../../stores/featuredReport';

/// Picker that lets the user choose which report fills the dashboard
/// widget's slot. Surfaces in the BriefingWidget's eyebrow row when
/// there's more than one report. With ≤1 report we render only the
/// label so the chevron doesn't promise an empty menu.
///
/// Wiring contract: this component does *not* fetch reports — that's
/// the responsibility of whichever view first lit them up (typically
/// the reports list). On a deep cold-start where only the dashboard
/// is rendered, we fetch lazily on first open. Once loaded, the
/// store keeps them around for the session.
///
/// Keyboard model: when the menu opens, the currently featured option
/// is highlighted (or the first option if nothing is featured). Arrow
/// up/down moves the highlight, Home/End jump to the ends, Enter
/// activates the highlighted item, Escape closes and returns focus to
/// the trigger.
interface FeaturedDropdownProps {
  /// The eyebrow text shown beside the chevron. Caller controls the
  /// label so this can read "BRIEFING · MAY 23" or just "DAILY
  /// BRIEFING" depending on context.
  label: string;
}

export const FeaturedDropdown = memo(function FeaturedDropdown({ label }: FeaturedDropdownProps) {
  const reports = useReportsStore(s => s.reports);
  const fetchAll = useReportsStore(s => s.fetchAll);
  const featuredId = useFeaturedReportStore(s => s.reportId);
  const setFeatured = useFeaturedReportStore(s => s.setFeatured);

  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Flat list of selectable items (reports + optional Unfeature row).
  // Used to drive keyboard navigation; reports.length doesn't change
  // mid-open in practice but we recompute on every render so a fresh
  // unsubscribe-driven update can't desync the highlight.
  const items = useMemo(() => {
    const list: ({ kind: 'report'; reportId: string } | { kind: 'unfeature' })[] =
      reports.map((r) => ({ kind: 'report' as const, reportId: r.id }));
    if (featuredId !== null) list.push({ kind: 'unfeature' });
    return list;
  }, [reports, featuredId]);

  // Lazy-fetch when the user first opens the picker. Idempotent; if
  // reports are already loaded the store no-ops.
  useEffect(() => {
    if (open && reports.length === 0) {
      void fetchAll();
    }
  }, [open, reports.length, fetchAll]);

  // When the menu opens, focus the currently featured option (or the
  // first item if nothing is featured). Defer to a microtask so the
  // dropdown has actually rendered.
  useEffect(() => {
    if (!open) return;
    const featuredIdx = items.findIndex(
      (it) => it.kind === 'report' && it.reportId === featuredId
    );
    const initial = featuredIdx >= 0 ? featuredIdx : 0;
    setHighlighted(initial);
    queueMicrotask(() => {
      itemRefs.current[initial]?.focus();
    });
  }, [open, items, featuredId]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [open]);

  const closeAndReturnFocus = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  const activate = useCallback((idx: number) => {
    const item = items[idx];
    if (!item) return;
    if (item.kind === 'report') {
      void setFeatured(item.reportId);
    } else {
      void setFeatured(null);
    }
    closeAndReturnFocus();
  }, [items, setFeatured, closeAndReturnFocus]);

  const onMenuKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (items.length === 0) return;
    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault();
        const next = (highlighted + 1) % items.length;
        setHighlighted(next);
        itemRefs.current[next]?.focus();
        break;
      }
      case 'ArrowUp': {
        e.preventDefault();
        const prev = (highlighted - 1 + items.length) % items.length;
        setHighlighted(prev);
        itemRefs.current[prev]?.focus();
        break;
      }
      case 'Home': {
        e.preventDefault();
        setHighlighted(0);
        itemRefs.current[0]?.focus();
        break;
      }
      case 'End': {
        e.preventDefault();
        const last = items.length - 1;
        setHighlighted(last);
        itemRefs.current[last]?.focus();
        break;
      }
      case 'Enter':
      case ' ': {
        e.preventDefault();
        activate(highlighted);
        break;
      }
      case 'Escape': {
        e.preventDefault();
        closeAndReturnFocus();
        break;
      }
    }
  }, [highlighted, items, activate, closeAndReturnFocus]);

  // With zero or one report, there's nothing to pick — render the
  // label without an interactive chevron.
  if (reports.length <= 1) {
    return (
      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-tertiary)]">
        {label}
      </span>
    );
  }

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(s => !s)}
        onKeyDown={(e) => {
          // Open with ArrowDown/Enter/Space; the open effect will
          // focus the right item.
          if (!open && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setOpen(true);
          }
        }}
        aria-haspopup="menu"
        aria-expanded={open}
        className="
          inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.14em]
          text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors
          focus:outline-none focus-visible:text-[var(--color-text-primary)]
        "
      >
        {label}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} strokeWidth={2.5} />
      </button>

      {open && (
        <div
          role="menu"
          onKeyDown={onMenuKeyDown}
          className="
            absolute left-0 mt-1.5 min-w-[220px] z-30
            bg-[var(--color-bg-card)] border border-[var(--color-border)]
            rounded-md shadow-xl py-1
            animate-in fade-in zoom-in-95 duration-100
          "
        >
          {reports.map((r, i) => {
            const isFeatured = featuredId === r.id;
            const isHighlighted = highlighted === i;
            return (
              <button
                key={r.id}
                ref={(el) => { itemRefs.current[i] = el; }}
                type="button"
                onClick={() => activate(i)}
                onMouseEnter={() => setHighlighted(i)}
                role="menuitemradio"
                aria-checked={isFeatured}
                tabIndex={-1}
                className={`
                  w-full px-3 py-1.5 text-left text-sm flex items-center gap-2
                  transition-colors focus:outline-none
                  ${isFeatured ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}
                  ${isHighlighted ? 'bg-[var(--color-bg-hover)]' : ''}
                `}
              >
                <span className="w-3.5 flex-shrink-0">
                  {isFeatured ? <Check className="w-3.5 h-3.5" strokeWidth={2.5} /> : null}
                </span>
                <Telescope className="w-3.5 h-3.5 flex-shrink-0 text-[var(--color-text-tertiary)]" strokeWidth={2} />
                <span className="truncate">{r.name}</span>
              </button>
            );
          })}
          {featuredId !== null && (
            <>
              <div className="my-1 border-t border-[var(--color-border)]" />
              <button
                ref={(el) => { itemRefs.current[reports.length] = el; }}
                type="button"
                onClick={() => activate(reports.length)}
                onMouseEnter={() => setHighlighted(reports.length)}
                role="menuitem"
                tabIndex={-1}
                className={`
                  w-full px-3 py-1.5 text-left text-sm
                  text-[var(--color-text-tertiary)]
                  transition-colors focus:outline-none
                  ${highlighted === reports.length ? 'bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]' : ''}
                `}
              >
                Unfeature
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
});
