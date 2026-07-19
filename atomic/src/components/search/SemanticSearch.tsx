import { useState, useEffect, useRef } from 'react';
import { Type, Lightbulb, Keyboard, Search, X, Check, Loader2 } from 'lucide-react';
import { useAtomsStore, SearchMode } from '../../stores/atoms';

const SEARCH_MODE_CONFIG: Record<SearchMode, { label: string; placeholder: string; icon: React.ReactNode }> = {
  keyword: {
    label: 'Keyword',
    placeholder: 'Search by keywords...',
    icon: <Type className="w-4 h-4" strokeWidth={2} />,
  },
  semantic: {
    label: 'Semantic',
    placeholder: 'Search by meaning...',
    icon: <Lightbulb className="w-4 h-4" strokeWidth={2} />,
  },
  hybrid: {
    label: 'Hybrid',
    placeholder: 'Search by keywords & meaning...',
    icon: <Keyboard className="w-4 h-4" strokeWidth={2} />,
  },
};

export function SemanticSearch() {
  const semanticSearchQuery = useAtomsStore(s => s.semanticSearchQuery);
  const search = useAtomsStore(s => s.search);
  const clearSemanticSearch = useAtomsStore(s => s.clearSemanticSearch);
  const isSearching = useAtomsStore(s => s.isSearching);
  const searchMode = useAtomsStore(s => s.searchMode);
  const setSearchMode = useAtomsStore(s => s.setSearchMode);

  const [inputValue, setInputValue] = useState(semanticSearchQuery);
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounce search by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      if (inputValue.trim()) {
        search(inputValue);
      } else {
        clearSemanticSearch();
      }
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputValue]);

  // Re-search when mode changes (if there's a query)
  useEffect(() => {
    if (inputValue.trim()) {
      search(inputValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchMode]);

  // Handle keyboard (Escape to clear)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setInputValue('');
      clearSemanticSearch();
      setShowModeDropdown(false);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showModeDropdown) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowModeDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showModeDropdown]);

  const currentConfig = SEARCH_MODE_CONFIG[searchMode];

  return (
    <div className="relative flex-1 min-w-0" ref={dropdownRef}>
      {/* Search icon button (opens mode dropdown) or loading spinner */}
      {isSearching ? (
        <Loader2
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)] animate-spin"
          strokeWidth={2}
        />
      ) : (
        <button
          onClick={() => setShowModeDropdown(!showModeDropdown)}
          className="absolute left-2 top-1/2 -translate-y-1/2 p-1 rounded text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] hover:bg-[var(--color-accent)]/10 transition-colors"
          title={`Search mode: ${currentConfig.label} (click to change)`}
        >
          <Search className="w-4 h-4" strokeWidth={2} />
        </button>
      )}

      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={currentConfig.placeholder}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        className="w-full pl-10 pr-10 py-2 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-md text-[var(--color-text-primary)] placeholder-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent transition-colors text-sm"
      />

      {/* Clear button */}
      {inputValue && (
        <button
          onClick={() => {
            setInputValue('');
            clearSemanticSearch();
            inputRef.current?.focus();
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <X className="w-4 h-4" strokeWidth={2} />
        </button>
      )}

      {/* Search mode dropdown */}
      {showModeDropdown && (
        <div className="absolute top-full left-0 mt-1 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-md shadow-lg z-50 min-w-[160px]">
          <div className="px-3 py-1.5 text-xs text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
            Search Mode
          </div>
          {(Object.keys(SEARCH_MODE_CONFIG) as SearchMode[]).map((mode) => {
            const config = SEARCH_MODE_CONFIG[mode];
            const isActive = mode === searchMode;
            return (
              <button
                key={mode}
                onClick={() => {
                  setSearchMode(mode);
                  setShowModeDropdown(false);
                  inputRef.current?.focus();
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                  isActive
                    ? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-panel)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {config.icon}
                <span>{config.label}</span>
                {isActive && (
                  <Check className="w-3.5 h-3.5 ml-auto" strokeWidth={2} />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
