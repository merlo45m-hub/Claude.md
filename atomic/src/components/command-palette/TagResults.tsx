import { memo, useEffect, useRef } from 'react';
import { Tag } from 'lucide-react';
import { TagWithCount } from './types';

interface TagResultsProps {
  tags: TagWithCount[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  query: string;
}

export const TagResults = memo(function TagResults({
  tags,
  selectedIndex,
  onSelect,
  query,
}: TagResultsProps) {
  // Empty state - no query
  if (!query.trim()) {
    return (
      <div className="overflow-y-auto max-h-[50vh] py-2">
        <div className="px-4 py-1.5 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wide">
          Popular Tags
        </div>
        {tags.length === 0 ? (
          <div className="px-4 py-8 text-center text-[var(--color-text-tertiary)] text-sm">
            No tags created yet
          </div>
        ) : (
          tags.map((tag, index) => (
            <TagResultItem
              key={tag.id}
              tag={tag}
              isSelected={selectedIndex === index}
              onClick={() => onSelect(index)}
              query=""
            />
          ))
        )}
      </div>
    );
  }

  // No results for query
  if (tags.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-[var(--color-text-tertiary)] text-sm">
        No tags found for "{query}"
      </div>
    );
  }

  return (
    <div className="overflow-y-auto max-h-[50vh] py-2">
      <div className="px-4 py-1.5 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wide flex items-center justify-between">
        <span>Matching Tags</span>
        <span className="normal-case font-normal">
          {tags.length} {tags.length === 1 ? 'tag' : 'tags'}
        </span>
      </div>

      {tags.map((tag, index) => (
        <TagResultItem
          key={tag.id}
          tag={tag}
          isSelected={selectedIndex === index}
          onClick={() => onSelect(index)}
          query={query}
        />
      ))}
    </div>
  );
});

interface TagResultItemProps {
  tag: TagWithCount;
  isSelected: boolean;
  onClick: () => void;
  query: string;
}

const TagResultItem = memo(function TagResultItem({
  tag,
  isSelected,
  onClick,
  query,
}: TagResultItemProps) {
  const ref = useRef<HTMLButtonElement>(null);

  // Scroll into view when selected
  useEffect(() => {
    if (isSelected && ref.current) {
      ref.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isSelected]);

  // Highlight matching part of tag name
  const highlightedName = query
    ? highlightMatch(tag.name, query)
    : [{ text: tag.name, highlighted: false }];

  return (
    <button
      ref={ref}
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors
        ${isSelected
          ? 'bg-[var(--color-bg-hover)] border-l-2 border-[var(--color-accent)]'
          : 'border-l-2 border-transparent hover:bg-[var(--color-bg-hover)]'
        }
      `}
    >
      <Tag className="w-4 h-4 text-[var(--color-text-secondary)] flex-shrink-0" strokeWidth={2} />

      <span className="flex-1 text-sm text-[var(--color-text-primary)]">
        {highlightedName.map((part, i) => (
          <span
            key={i}
            className={part.highlighted ? 'text-[var(--color-accent)] font-medium' : ''}
          >
            {part.text}
          </span>
        ))}
      </span>

      <span className="text-xs text-[var(--color-text-tertiary)]">
        {tag.atom_count} {tag.atom_count === 1 ? 'atom' : 'atoms'}
      </span>
    </button>
  );
});

// Simple substring highlighting (not fuzzy)
function highlightMatch(
  text: string,
  query: string
): { text: string; highlighted: boolean }[] {
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);

  if (index === -1) {
    return [{ text, highlighted: false }];
  }

  const result: { text: string; highlighted: boolean }[] = [];

  if (index > 0) {
    result.push({ text: text.slice(0, index), highlighted: false });
  }

  result.push({ text: text.slice(index, index + query.length), highlighted: true });

  if (index + query.length < text.length) {
    result.push({ text: text.slice(index + query.length), highlighted: false });
  }

  return result;
}
