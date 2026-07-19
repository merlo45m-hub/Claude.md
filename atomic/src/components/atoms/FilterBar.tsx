import { useState, useRef, useEffect } from 'react';
import { Filter, X, ArrowDownUp } from 'lucide-react';
import { useAtomsStore, SourceFilterType, SortField, SortOrder } from '../../stores/atoms';

const SORT_OPTIONS: { field: SortField; order: SortOrder; label: string }[] = [
  { field: 'updated', order: 'desc', label: 'Updated (newest)' },
  { field: 'updated', order: 'asc', label: 'Updated (oldest)' },
  { field: 'created', order: 'desc', label: 'Created (newest)' },
  { field: 'created', order: 'asc', label: 'Created (oldest)' },
  { field: 'published', order: 'desc', label: 'Published (newest)' },
  { field: 'published', order: 'asc', label: 'Published (oldest)' },
  { field: 'title', order: 'asc', label: 'Title (A-Z)' },
  { field: 'title', order: 'desc', label: 'Title (Z-A)' },
];

export function FilterBar() {
  const sourceFilter = useAtomsStore(s => s.sourceFilter);
  const sourceValue = useAtomsStore(s => s.sourceValue);
  const sortBy = useAtomsStore(s => s.sortBy);
  const sortOrder = useAtomsStore(s => s.sortOrder);
  const availableSources = useAtomsStore(s => s.availableSources);
  const setSourceFilter = useAtomsStore(s => s.setSourceFilter);
  const setSourceValue = useAtomsStore(s => s.setSourceValue);
  const setSortBy = useAtomsStore(s => s.setSortBy);
  const setSortOrder = useAtomsStore(s => s.setSortOrder);
  const fetchSources = useAtomsStore(s => s.fetchSources);
  const clearFilters = useAtomsStore(s => s.clearFilters);

  const [showSourceDropdown, setShowSourceDropdown] = useState(false);
  const [showSortDropdown, setShowSortDropdown] = useState(false);
  const sourceDropdownRef = useRef<HTMLDivElement>(null);
  const sortDropdownRef = useRef<HTMLDivElement>(null);

  // Fetch sources on mount
  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (sourceDropdownRef.current && !sourceDropdownRef.current.contains(e.target as Node)) {
        setShowSourceDropdown(false);
      }
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(e.target as Node)) {
        setShowSortDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const currentSort = SORT_OPTIONS.find(o => o.field === sortBy && o.order === sortOrder) ?? SORT_OPTIONS[0];

  const handleSourceFilterChange = (filter: SourceFilterType) => {
    setSourceFilter(filter);
    setShowSourceDropdown(false);
  };

  const handleSourceValueChange = (value: string) => {
    setSourceValue(value);
    setShowSourceDropdown(false);
  };

  const handleSortChange = (field: SortField, order: SortOrder) => {
    setSortBy(field);
    setSortOrder(order);
    setShowSortDropdown(false);
  };

  return (
    <div className="flex items-center gap-2 px-4 py-1.5 mb-1 border-b border-[var(--color-border)] bg-[var(--color-bg-main)]">
      {/* Filter dropdown + chips */}
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        {/* Filter dropdown — always first so it doesn't shift */}
        <div className="relative shrink-0" ref={sourceDropdownRef}>
          <button
            onClick={() => { setShowSourceDropdown(!showSourceDropdown); setShowSortDropdown(false); }}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <Filter className="w-3.5 h-3.5" strokeWidth={2} />
            Filter
          </button>

          {showSourceDropdown && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg shadow-lg z-50 overflow-hidden">
              <div className="px-3 py-2 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider border-b border-[var(--color-border)]">
                Source
              </div>
              <div className="py-1">
                <button
                  onClick={() => handleSourceFilterChange('all')}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-bg-hover)] transition-colors ${sourceFilter === 'all' && !sourceValue ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}`}
                >
                  All atoms
                </button>
                <button
                  onClick={() => handleSourceFilterChange('manual')}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-bg-hover)] transition-colors ${sourceFilter === 'manual' ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}`}
                >
                  Manual / user-written
                </button>
                <button
                  onClick={() => handleSourceFilterChange('external')}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-bg-hover)] transition-colors ${sourceFilter === 'external' && !sourceValue ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}`}
                >
                  External / synced
                </button>
              </div>

              {availableSources.length > 0 && (
                <>
                  <div className="px-3 py-2 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider border-t border-[var(--color-border)]">
                    Specific source
                  </div>
                  <div className="py-1 max-h-48 overflow-y-auto">
                    {availableSources.map(s => (
                      <button
                        key={s.source}
                        onClick={() => handleSourceValueChange(s.source)}
                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-bg-hover)] transition-colors flex items-center justify-between ${sourceValue === s.source ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}`}
                      >
                        <span className="truncate">{s.source}</span>
                        <span className="text-xs text-[var(--color-text-tertiary)] ml-2 shrink-0">{s.atom_count}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Active filter chips — appear after the dropdown trigger */}
        {sourceFilter !== 'all' && !sourceValue && (
          <button
            onClick={() => setSourceFilter('all')}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-[var(--color-accent)]/15 text-[var(--color-accent-light)] hover:bg-[var(--color-accent)]/25 transition-colors"
          >
            {sourceFilter === 'manual' ? 'Manual' : 'External'}
            <X className="w-3 h-3" strokeWidth={2} />
          </button>
        )}

        {sourceValue && (
          <button
            onClick={() => setSourceValue(null)}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-[var(--color-accent)]/15 text-[var(--color-accent-light)] hover:bg-[var(--color-accent)]/25 transition-colors truncate max-w-[200px]"
          >
            {sourceValue}
            <X className="w-3 h-3 shrink-0" strokeWidth={2} />
          </button>
        )}

        {/* Clear all filters */}
        {(sourceFilter !== 'all' || sourceValue) && (
          <button
            onClick={clearFilters}
            className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Sort dropdown */}
      <div className="relative shrink-0" ref={sortDropdownRef}>
        <button
          onClick={() => { setShowSortDropdown(!showSortDropdown); setShowSourceDropdown(false); }}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
        >
          <ArrowDownUp className="w-3.5 h-3.5" strokeWidth={2} />
          {currentSort.label}
        </button>

        {showSortDropdown && (
          <div className="absolute top-full right-0 mt-1 w-48 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg shadow-lg z-50 overflow-hidden">
            <div className="py-1">
              {SORT_OPTIONS.map(opt => (
                <button
                  key={`${opt.field}-${opt.order}`}
                  onClick={() => handleSortChange(opt.field, opt.order)}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-[var(--color-bg-hover)] transition-colors ${sortBy === opt.field && sortOrder === opt.order ? 'text-[var(--color-accent-light)]' : 'text-[var(--color-text-primary)]'}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
