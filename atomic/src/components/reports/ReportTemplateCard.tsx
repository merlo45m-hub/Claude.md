import { memo } from 'react';
import { FilePlus, LucideIcon } from 'lucide-react';
import { ReportTemplate } from '../../lib/reportTemplates';

interface ReportTemplateCardProps {
  /// When `template` is provided, renders a real template card.
  /// When omitted, renders the "Start blank" affordance — same
  /// geometry, lighter chrome, no schedule hint.
  template?: ReportTemplate;
  onClick: () => void;
}

/// One card in the template gallery. Slim rectangular tile; icon
/// floats top-left, name and description stack to its right, schedule
/// hint pinned to the bottom as an eyebrow chip.
export const ReportTemplateCard = memo(function ReportTemplateCard({
  template, onClick,
}: ReportTemplateCardProps) {
  const isBlank = !template;
  const Icon: LucideIcon = template?.icon ?? FilePlus;
  const name = template?.body.name ?? 'Start blank';
  const description = template?.description ?? 'Build a report from scratch with no presets.';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        group flex flex-col gap-2 p-4 rounded-lg
        text-left transition-colors
        border
        ${isBlank
          ? 'border-dashed border-[var(--color-border)] hover:border-[var(--color-border-hover)] hover:bg-[var(--color-bg-hover)]'
          : 'border-[var(--color-border)] bg-[var(--color-bg-card)] hover:border-[var(--color-accent)]/40 hover:bg-[var(--color-bg-hover)]'
        }
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`
          flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center
          ${isBlank
            ? 'bg-[var(--color-bg-hover)] text-[var(--color-text-tertiary)]'
            : 'bg-[var(--color-accent)]/10 text-[var(--color-accent-light)]'
          }
        `}>
          <Icon className="w-4 h-4" strokeWidth={2} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-medium text-[var(--color-text-primary)] mb-1">
            {name}
          </h3>
          <p className="text-[12px] text-[var(--color-text-secondary)] leading-snug">
            {description}
          </p>
        </div>
      </div>
      {template && (
        <div className="
          mt-1 text-[10px] font-medium uppercase tracking-[0.12em]
          text-[var(--color-text-tertiary)] font-mono
        ">
          {template.scheduleHint}
        </div>
      )}
    </button>
  );
});
