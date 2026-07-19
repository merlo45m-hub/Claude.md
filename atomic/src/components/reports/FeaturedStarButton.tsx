import { memo, useEffect } from 'react';
import { Star } from 'lucide-react';
import { getTransport } from '../../lib/transport';
import { useFeaturedReportStore } from '../../stores/featuredReport';

interface FeaturedStarButtonProps {
  reportId: string;
}

/// Star toggle that controls whether this report is the dashboard's
/// featured report. Reads from `useFeaturedReportStore.reportId` so
/// the visual state stays consistent across windows (the
/// `dashboard-featured-changed` event triggers a refetch when another
/// client toggles the pointer).
export const FeaturedStarButton = memo(function FeaturedStarButton({ reportId }: FeaturedStarButtonProps) {
  const currentFeatured = useFeaturedReportStore(s => s.reportId);
  const fetchLatest = useFeaturedReportStore(s => s.fetchLatest);
  const setFeatured = useFeaturedReportStore(s => s.setFeatured);

  // Make sure we know the current featured-id when this button is rendered.
  // featuredReportStore lazy-loads on its first consumer (the BriefingWidget),
  // but a deep-link to a detail view bypasses that — pull on mount.
  useEffect(() => {
    if (currentFeatured === null) {
      fetchLatest();
    }
    // We only care about the cold-start case; subsequent featured
    // changes flow through the cross-window event.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Subscribe to cross-window updates. Re-runs `fetchLatest` so this
  // button's state matches reality without polling.
  useEffect(() => {
    const unsub = getTransport().subscribe('dashboard-featured-changed', () => {
      void fetchLatest();
    });
    return () => unsub();
  }, [fetchLatest]);

  const isFeatured = currentFeatured === reportId;

  const handleClick = () => {
    void setFeatured(isFeatured ? null : reportId);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title={isFeatured ? 'Featured on dashboard' : 'Feature on dashboard'}
      aria-label={isFeatured ? 'Unfeature from dashboard' : 'Feature on dashboard'}
      aria-pressed={isFeatured}
      className={`
        p-1 rounded-md transition-colors
        ${isFeatured
          ? 'text-[var(--color-accent-light)] hover:text-[var(--color-accent)]'
          : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]'
        }
      `}
    >
      <Star className="w-4 h-4" strokeWidth={2} fill={isFeatured ? 'currentColor' : 'none'} />
    </button>
  );
});
