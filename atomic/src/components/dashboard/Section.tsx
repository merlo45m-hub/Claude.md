import type { ReactNode } from 'react';

interface SectionProps {
  label: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ label, action, children, className = '' }: SectionProps) {
  return (
    <section className={className}>
      <header className="flex items-center gap-3 mb-3 h-5">
        <h3 className="text-[11px] leading-none font-medium uppercase tracking-[0.14em] text-[var(--color-text-tertiary)] whitespace-nowrap">
          {label}
        </h3>
        <div className="flex-1 h-px bg-[var(--color-border)]" />
        {action && <div className="shrink-0 leading-none">{action}</div>}
      </header>
      {children}
    </section>
  );
}
