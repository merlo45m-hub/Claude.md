import { memo, useEffect, useRef } from 'react';
import { Command, FuzzyMatch } from './types';
import { highlightMatches } from './fuzzySearch';

interface CommandItemProps {
  command: Command;
  matches?: number[];
  isSelected: boolean;
  onClick: () => void;
}

export const CommandItem = memo(function CommandItem({
  command,
  matches = [],
  isSelected,
  onClick,
}: CommandItemProps) {
  const ref = useRef<HTMLButtonElement>(null);

  // Scroll into view when selected
  useEffect(() => {
    if (isSelected && ref.current) {
      ref.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isSelected]);

  const highlightedLabel = highlightMatches(command.label, matches);
  const Icon = command.icon;

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
      {Icon && (
        <span className="text-[var(--color-text-secondary)] flex-shrink-0">
          <Icon />
        </span>
      )}

      <span className="flex-1 text-sm text-[var(--color-text-primary)]">
        {highlightedLabel.map((part, i) => (
          <span
            key={i}
            className={part.highlighted ? 'text-[var(--color-accent)] font-medium' : ''}
          >
            {part.text}
          </span>
        ))}
      </span>

      {command.shortcut && (
        <kbd className="px-1.5 py-0.5 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded text-[10px] font-mono text-[var(--color-text-tertiary)]">
          {command.shortcut}
        </kbd>
      )}
    </button>
  );
});

// Wrapper for FuzzyMatch results
interface CommandMatchItemProps {
  match: FuzzyMatch;
  isSelected: boolean;
  onClick: () => void;
}

export const CommandMatchItem = memo(function CommandMatchItem({
  match,
  isSelected,
  onClick,
}: CommandMatchItemProps) {
  return (
    <CommandItem
      command={match.command}
      matches={match.matches}
      isSelected={isSelected}
      onClick={onClick}
    />
  );
});
