import { Section } from '../Section';
import { useWikiStore } from '../../../stores/wiki';

const MAX_ITEMS = 5;

export function NewWikisWidget() {
  const suggestedArticles = useWikiStore(s => s.suggestedArticles);
  const openAndGenerate = useWikiStore(s => s.openAndGenerate);

  const items = suggestedArticles.slice(0, MAX_ITEMS);

  return (
    <Section label="Ready to generate">
      {items.length === 0 ? (
        <div className="py-6 text-sm text-[var(--color-text-tertiary)]">
          No wiki suggestions yet. Tag more atoms to build up candidates.
        </div>
      ) : (
        <ul className="-mx-2">
          {items.map(s => (
            <li key={s.tag_id}>
              <button
                onClick={() => openAndGenerate(s.tag_id, s.tag_name)}
                className="w-full flex items-baseline gap-3 px-2 py-1.5 rounded hover:bg-[var(--color-bg-hover)]/60 text-left group"
              >
                <span className="flex-1 min-w-0 truncate text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]">
                  {s.tag_name}
                </span>
                <span className="text-[11px] text-[var(--color-text-tertiary)] tabular-nums shrink-0">
                  {s.atom_count} atoms
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
