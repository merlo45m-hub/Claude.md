import { useEmbeddingProgressStore } from '../../stores/embedding-progress';

const MIN_REMAINING_TO_SHOW = 2;

function RemainingRow({ label, count }: { label: string; count: number }) {
  if (count <= 0) return null;

  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-[var(--color-text-secondary)]">{label}</span>
      <span className="font-medium tabular-nums text-[var(--color-text-primary)]">
        {count.toLocaleString()} remaining
      </span>
    </div>
  );
}

export function EmbeddingProgressBanner() {
  const embeddingRemaining = useEmbeddingProgressStore(s => s.embeddingRemaining);
  const taggingRemaining = useEmbeddingProgressStore(s => s.taggingRemaining);
  const totalRemaining = embeddingRemaining + taggingRemaining;

  if (totalRemaining < MIN_REMAINING_TO_SHOW) return null;

  return (
    <div className="fixed bottom-4 left-4 z-[70] w-72 px-3 py-2.5 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg shadow-lg pointer-events-none animate-in fade-in slide-in-from-bottom-2 duration-200">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-[var(--color-text-primary)]">AI processing</span>
        <span className="text-[10px] tabular-nums text-[var(--color-text-tertiary)]">
          {totalRemaining.toLocaleString()} queued
        </span>
      </div>
      <div className="space-y-1.5">
        <RemainingRow label="Embeddings" count={embeddingRemaining} />
        <RemainingRow label="Tagging" count={taggingRemaining} />
      </div>
    </div>
  );
}
