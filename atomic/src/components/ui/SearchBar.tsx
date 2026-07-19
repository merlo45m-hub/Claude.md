import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, ChevronUp, ChevronDown, X, Loader2 } from 'lucide-react';

const DEBOUNCE_MS = 200;

interface SearchBarProps {
  query: string;
  searchedQuery: string; // The query that totalMatches corresponds to
  onQueryChange: (q: string) => void;
  currentIndex: number;
  totalMatches: number;
  onNext: () => void;
  onPrevious: () => void;
  onClose: () => void;
}

export function SearchBar({
  query,
  searchedQuery,
  onQueryChange,
  currentIndex,
  totalMatches,
  onNext,
  onPrevious,
  onClose,
}: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  // Local input state for responsive typing - doesn't cause parent re-renders
  const [localValue, setLocalValue] = useState(query);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Pending if local value differs from what's been searched
  const isPending = localValue.trim() !== '' && localValue !== searchedQuery;

  // Auto-focus input when mounted
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handleChange = useCallback((value: string) => {
    setLocalValue(value);

    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Set new debounced update
    timerRef.current = setTimeout(() => {
      onQueryChange(value);
    }, DEBOUNCE_MS);
  }, [onQueryChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) {
        onPrevious();
      } else {
        onNext();
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      onNext();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      onPrevious();
    }
  };

  const getMatchText = () => {
    if (!localValue.trim()) return null;
    if (isPending) {
      // Animated ring loader
      return (
        <Loader2 className="w-4 h-4 animate-spin text-[var(--color-accent)]" strokeWidth={2} />
      );
    }
    if (totalMatches === 0) return 'No matches';
    return `${currentIndex + 1} of ${totalMatches}`;
  };

  return (
    <div className="sticky left-0 right-0 top-0 z-20 px-4 py-2 bg-[var(--color-bg-card)] border-b border-[var(--color-border)] shadow-lg">
      <div className="flex items-center gap-2">
        {/* Search icon */}
        <Search className="w-4 h-4 text-[var(--color-text-secondary)] flex-shrink-0" strokeWidth={2} />

        {/* Search input */}
        <input
          ref={inputRef}
          type="text"
          value={localValue}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Find in content..."
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          className="flex-1 bg-transparent text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none text-sm"
        />

        {/* Match counter / loading indicator */}
        {localValue.trim() && (
          <span className="text-xs text-[var(--color-text-secondary)] whitespace-nowrap flex items-center">
            {getMatchText()}
          </span>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={onPrevious}
            disabled={isPending || totalMatches === 0}
            className="p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Previous match (Shift+Enter)"
          >
            <ChevronUp className="w-4 h-4" strokeWidth={2} />
          </button>
          <button
            onClick={onNext}
            disabled={isPending || totalMatches === 0}
            className="p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title="Next match (Enter)"
          >
            <ChevronDown className="w-4 h-4" strokeWidth={2} />
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          title="Close (Escape)"
        >
          <X className="w-4 h-4" strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
