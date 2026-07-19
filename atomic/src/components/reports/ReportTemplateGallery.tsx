import { memo } from 'react';
import { Modal } from '../ui/Modal';
import { REPORT_TEMPLATES, ReportTemplate } from '../../lib/reportTemplates';
import { ReportTemplateCard } from './ReportTemplateCard';

interface ReportTemplateGalleryProps {
  /// When `mode === 'modal'`, the gallery renders inside a Modal with
  /// its own title bar. When `mode === 'inline'`, it renders a plain
  /// section suitable for the empty-state of ReportsList.
  mode: 'modal' | 'inline';
  /// Modal-only: whether the modal is open. Ignored when inline.
  isOpen?: boolean;
  onClose?: () => void;
  /// Receives the picked template (or `null` for "Start blank"). The
  /// caller handles opening the editor with the right initial body.
  onPick: (template: ReportTemplate | null) => void;
}

/// Grid of curated template cards plus a "Start blank" card. The grid
/// is 2-up on `sm` and wider, single-column on narrow viewports.
const TemplateGrid = memo(function TemplateGrid({
  onPick,
}: { onPick: (template: ReportTemplate | null) => void }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {REPORT_TEMPLATES.map((t) => (
        <ReportTemplateCard
          key={t.id}
          template={t}
          onClick={() => onPick(t)}
        />
      ))}
      <ReportTemplateCard onClick={() => onPick(null)} />
    </div>
  );
});

export const ReportTemplateGallery = memo(function ReportTemplateGallery({
  mode, isOpen, onClose, onPick,
}: ReportTemplateGalleryProps) {
  if (mode === 'modal') {
    return (
      <Modal
        isOpen={isOpen ?? false}
        onClose={onClose ?? (() => undefined)}
        title="New report"
        width="lg"
        showFooter={false}
      >
        <p className="text-sm text-[var(--color-text-secondary)] mb-4 leading-relaxed">
          Pick a template to get started, or build your own. You can rename,
          re-scope, and rewrite the prompt before saving.
        </p>
        <TemplateGrid onPick={onPick} />
      </Modal>
    );
  }

  // Inline mode (empty-state). Renders without a modal wrapper, but
  // wraps the grid in a clearly bounded panel so it reads as a
  // standalone block rather than naked cards.
  return (
    <section className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-5">
        <h2 className="text-base font-medium text-[var(--color-text-primary)] mb-1">
          Start your first report
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          Reports run on a schedule and produce findings that join your atoms.
          Pick a template below, or start blank.
        </p>
      </header>
      <TemplateGrid onPick={onPick} />
    </section>
  );
});
