import { Loader2 } from 'lucide-react';

interface WikiGeneratingProps {
  tagName: string;
  atomCount: number;
}

export function WikiGenerating({ tagName, atomCount }: WikiGeneratingProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 text-center">
      {/* Spinner */}
      <Loader2 className="w-16 h-16 mb-6 animate-spin text-[var(--color-accent)]" strokeWidth={2} />
      
      <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2">
        Synthesizing article about "{tagName}"...
      </h3>
      
      <p className="text-sm text-[var(--color-text-secondary)]">
        Processing {atomCount} source{atomCount !== 1 ? 's' : ''}
      </p>
      
      <p className="text-xs text-[var(--color-text-tertiary)] mt-4">
        This may take a moment
      </p>
    </div>
  );
}

