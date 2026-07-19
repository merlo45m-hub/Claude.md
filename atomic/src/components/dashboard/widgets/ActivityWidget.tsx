import { useMemo } from 'react';
import { Section } from '../Section';
import { useAtomsStore } from '../../../stores/atoms';
import { useWikiStore } from '../../../stores/wiki';
import { useUIStore } from '../../../stores/ui';
import { formatShortRelativeDate } from '../../../lib/date';

type FeedItem =
  | { kind: 'atom'; id: string; title: string; timestamp: string }
  | { kind: 'wiki'; id: string; tagId: string; title: string; timestamp: string };

const MAX_ITEMS = 8;

export function ActivityWidget() {
  const atoms = useAtomsStore(s => s.atoms);
  const articles = useWikiStore(s => s.articles);
  const openReader = useUIStore(s => s.openReader);
  const openWikiReader = useUIStore(s => s.openWikiReader);

  const items = useMemo<FeedItem[]>(() => {
    const atomItems: FeedItem[] = atoms.slice(0, MAX_ITEMS * 2).map(a => ({
      kind: 'atom',
      id: a.id,
      title: a.title || 'Untitled atom',
      timestamp: a.updated_at,
    }));
    const wikiItems: FeedItem[] = articles.slice(0, MAX_ITEMS).map(w => ({
      kind: 'wiki',
      id: w.id,
      tagId: w.tag_id,
      title: w.tag_name,
      timestamp: w.updated_at,
    }));
    return [...atomItems, ...wikiItems]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, MAX_ITEMS);
  }, [atoms, articles]);

  return (
    <Section label="Recent activity">
      {items.length === 0 ? (
        <EmptyState>Activity will appear here as atoms and wikis land.</EmptyState>
      ) : (
        <ul className="-mx-2">
          {items.map(item => (
            <li key={`${item.kind}-${item.id}`}>
              <button
                onClick={() =>
                  item.kind === 'atom'
                    ? openReader(item.id)
                    : openWikiReader(item.tagId, item.title)
                }
                className="w-full flex items-baseline gap-3 px-2 py-1.5 rounded hover:bg-[var(--color-bg-hover)]/60 text-left group"
              >
                <span className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] w-10 shrink-0">
                  {item.kind === 'atom' ? 'atom' : 'wiki'}
                </span>
                <span className="flex-1 min-w-0 truncate text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]">
                  {item.title}
                </span>
                <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums shrink-0">
                  {formatShortRelativeDate(item.timestamp)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="py-6 text-sm text-[var(--color-text-tertiary)]">
      {children}
    </div>
  );
}
