import { useMemo } from 'react';
import { Section } from '../Section';
import { useWikiStore } from '../../../stores/wiki';
import { useTagsStore, type TagWithCount } from '../../../stores/tags';
import { useUIStore } from '../../../stores/ui';

const MAX_ITEMS = 5;

function findTag(nodes: TagWithCount[], id: string): TagWithCount | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children.length) {
      const found = findTag(n.children, id);
      if (found) return found;
    }
  }
  return null;
}

interface RevisionItem {
  tagId: string;
  tagName: string;
  delta: number;
}

export function RevisionsWidget() {
  const articles = useWikiStore(s => s.articles);
  const tags = useTagsStore(s => s.tags);
  const openWikiReader = useUIStore(s => s.openWikiReader);

  const items = useMemo<RevisionItem[]>(() => {
    const results: RevisionItem[] = [];
    for (const a of articles) {
      const tag = findTag(tags, a.tag_id);
      if (!tag) continue;
      const delta = tag.atom_count - a.atom_count;
      if (delta > 0) {
        results.push({ tagId: a.tag_id, tagName: a.tag_name, delta });
      }
    }
    return results.sort((x, y) => y.delta - x.delta).slice(0, MAX_ITEMS);
  }, [articles, tags]);

  return (
    <Section label="Revision suggestions">
      {items.length === 0 ? (
        <div className="py-6 text-sm text-[var(--color-text-tertiary)]">
          {articles.length > 0 ? 'All wikis are up to date.' : 'Generate a wiki to start tracking revisions.'}
        </div>
      ) : (
        <ul className="-mx-2">
          {items.map(item => (
            <li key={item.tagId}>
              <button
                onClick={() => openWikiReader(item.tagId, item.tagName)}
                className="w-full flex items-baseline gap-3 px-2 py-1.5 rounded hover:bg-[var(--color-bg-hover)]/60 text-left group"
              >
                <span className="flex-1 min-w-0 truncate text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]">
                  {item.tagName}
                </span>
                <span className="text-[11px] text-amber-400/90 tabular-nums shrink-0">
                  +{item.delta}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
