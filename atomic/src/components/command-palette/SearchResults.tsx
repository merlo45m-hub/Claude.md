import { memo, useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import { SemanticSearchResult } from './types';

interface SearchResultsProps {
  results: SemanticSearchResult[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  isSearching: boolean;
  query: string;
}

export const SearchResults = memo(function SearchResults({
  results,
  selectedIndex,
  onSelect,
  isSearching,
  query,
}: SearchResultsProps) {
  // Empty state - still typing
  if (!query.trim()) {
    return (
      <div className="px-4 py-8 text-center text-[var(--color-text-tertiary)] text-sm">
        Type at least 2 characters to search...
      </div>
    );
  }

  // Loading state
  if (isSearching) {
    return (
      <div className="px-4 py-8 text-center text-[var(--color-text-tertiary)] text-sm">
        <span className="inline-flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2} />
          Searching...
        </span>
      </div>
    );
  }

  // No results
  if (results.length === 0 && query.trim().length >= 2) {
    return (
      <div className="px-4 py-8 text-center text-[var(--color-text-tertiary)] text-sm">
        No atoms found for "{query}"
      </div>
    );
  }

  return (
    <div className="overflow-y-auto max-h-[50vh] py-2">
      <div className="px-4 py-1.5 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wide flex items-center justify-between">
        <span>Search Results</span>
        <span className="normal-case font-normal">
          {results.length} {results.length === 1 ? 'result' : 'results'}
        </span>
      </div>

      {results.map((result, index) => (
        <SearchResultItem
          key={result.id}
          result={result}
          isSelected={selectedIndex === index}
          onClick={() => onSelect(index)}
        />
      ))}
    </div>
  );
});

interface SearchResultItemProps {
  result: SemanticSearchResult;
  isSelected: boolean;
  onClick: () => void;
}

const SearchResultItem = memo(function SearchResultItem({
  result,
  isSelected,
  onClick,
}: SearchResultItemProps) {
  const ref = useRef<HTMLButtonElement>(null);

  // Scroll into view when selected
  useEffect(() => {
    if (isSelected && ref.current) {
      ref.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isSelected]);

  // Get a preview of the content
  const preview = result.matching_chunk_content
    ? result.matching_chunk_content.slice(0, 150).trim()
    : result.content.slice(0, 150).trim();

  // Format similarity score
  const scorePercent = Math.round(result.similarity_score * 100);

  return (
    <button
      ref={ref}
      onClick={onClick}
      className={`
        w-full flex flex-col gap-1 px-4 py-3 text-left transition-colors
        ${isSelected
          ? 'bg-[var(--color-bg-hover)] border-l-2 border-[var(--color-accent)]'
          : 'border-l-2 border-transparent hover:bg-[var(--color-bg-hover)]'
        }
      `}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono px-1.5 py-0.5 bg-[var(--color-accent-alpha)] text-[var(--color-accent)] rounded">
          {scorePercent}%
        </span>
        <span className="flex-1 text-sm font-medium text-[var(--color-text-primary)] truncate">
          {getTitle(result.content)}
        </span>
      </div>

      <p className="text-xs text-[var(--color-text-secondary)] line-clamp-2">
        {preview}...
      </p>

      {result.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap mt-0.5">
          {result.tags.slice(0, 3).map((tag) => (
            <span
              key={tag.id}
              className="text-[10px] px-1.5 py-0.5 bg-[var(--color-bg-card)] text-[var(--color-text-tertiary)] rounded"
            >
              #{tag.name}
            </span>
          ))}
          {result.tags.length > 3 && (
            <span className="text-[10px] text-[var(--color-text-tertiary)]">
              +{result.tags.length - 3}
            </span>
          )}
        </div>
      )}
    </button>
  );
});

// Extract a title from content (first line or first N characters)
function getTitle(content: string): string {
  const firstLine = content.split('\n')[0].trim();

  // Remove markdown headers
  const withoutHeader = firstLine.replace(/^#+\s*/, '');

  if (withoutHeader.length > 60) {
    return withoutHeader.slice(0, 60) + '...';
  }

  return withoutHeader || 'Untitled';
}
