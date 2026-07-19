import { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import type { AvailableModel } from '../../lib/api';

// Fuzzy search function - checks if search chars appear in order in target
function fuzzyMatch(search: string, target: string): { match: boolean; score: number } {
  const searchLower = search.toLowerCase();
  const targetLower = target.toLowerCase();

  if (!search) return { match: true, score: 1 };

  // Exact match gets highest score
  if (targetLower.includes(searchLower)) {
    return { match: true, score: 2 + (1 - searchLower.length / targetLower.length) };
  }

  // Fuzzy match - chars must appear in order
  let searchIdx = 0;
  let consecutiveBonus = 0;
  let lastMatchIdx = -2;

  for (let i = 0; i < targetLower.length && searchIdx < searchLower.length; i++) {
    if (targetLower[i] === searchLower[searchIdx]) {
      if (i === lastMatchIdx + 1) consecutiveBonus += 0.1;
      lastMatchIdx = i;
      searchIdx++;
    }
  }

  if (searchIdx === searchLower.length) {
    return { match: true, score: 1 + consecutiveBonus };
  }

  return { match: false, score: 0 };
}

interface SearchableSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: AvailableModel[];
  isLoading?: boolean;
  placeholder?: string;
}

export function SearchableSelect({ value, onChange, options, isLoading, placeholder = 'Select...' }: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const selectRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Find selected option
  const selectedOption = options.find(opt => opt.id === value);

  // Filter and sort options by fuzzy match
  const filteredOptions = options
    .map(opt => ({
      ...opt,
      ...fuzzyMatch(search, `${opt.name} ${opt.id}`)
    }))
    .filter(opt => opt.match)
    .sort((a, b) => b.score - a.score);

  // Reset highlight when filtered options change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [search]);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlighted = listRef.current.querySelector('[data-highlighted="true"]');
      if (highlighted) {
        highlighted.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, isOpen]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch('');
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => Math.min(prev + 1, filteredOptions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredOptions[highlightedIndex]) {
          onChange(filteredOptions[highlightedIndex].id);
          setIsOpen(false);
          setSearch('');
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setSearch('');
        break;
    }
  }, [isOpen, filteredOptions, highlightedIndex, onChange]);

  const handleOpen = () => {
    setIsOpen(true);
    setSearch('');
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  return (
    <div ref={selectRef} className="relative">
      {/* Selected value / trigger button */}
      <button
        type="button"
        onClick={handleOpen}
        onKeyDown={handleKeyDown}
        className="w-full px-3 py-2 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] text-left text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent transition-colors duration-150 flex items-center justify-between"
      >
        <span className={selectedOption ? '' : 'text-[var(--color-text-secondary)]'}>
          {isLoading ? 'Loading models...' : (selectedOption?.name || value || placeholder)}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-[var(--color-text-secondary)] transition-transform ${isOpen ? 'rotate-180' : ''}`}
          strokeWidth={2}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-md shadow-lg overflow-hidden">
          {/* Search input */}
          <div className="p-2 border-b border-[var(--color-border)]">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search models..."
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              className="w-full px-2 py-1.5 bg-[var(--color-bg-main)] border border-[var(--color-border)] rounded text-[var(--color-text-primary)] text-sm placeholder-[var(--color-text-secondary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
          </div>

          {/* Options list */}
          <div ref={listRef} className="max-h-60 overflow-y-auto">
            {isLoading ? (
              <div className="px-3 py-4 text-center text-sm text-[var(--color-text-secondary)]">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" strokeWidth={2} />
                Loading models...
              </div>
            ) : filteredOptions.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-[var(--color-text-secondary)]">
                No models found
              </div>
            ) : (
              filteredOptions.map((option, index) => (
                <button
                  key={option.id}
                  type="button"
                  data-highlighted={index === highlightedIndex}
                  onClick={() => {
                    onChange(option.id);
                    setIsOpen(false);
                    setSearch('');
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`w-full px-3 py-2 text-left text-sm transition-colors ${
                    option.id === value
                      ? 'bg-[var(--color-accent)] text-white'
                      : index === highlightedIndex
                      ? 'bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]'
                      : 'text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)]'
                  }`}
                >
                  <div className="font-medium">{option.name}</div>
                  <div className={`text-xs ${option.id === value ? 'text-white/70' : 'text-[var(--color-text-secondary)]'}`}>
                    {option.id}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
