import { Loader2 } from 'lucide-react';

export function ConnectionStatus({ status, error }: { status: 'checking' | 'connected' | 'disconnected'; error?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {status === 'checking' && (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-secondary)]" strokeWidth={2} />
          <span className="text-[var(--color-text-secondary)]">Checking connection...</span>
        </>
      )}
      {status === 'connected' && (
        <>
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-green-500">Connected</span>
        </>
      )}
      {status === 'disconnected' && (
        <>
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-red-500">{error || 'Not connected'}</span>
        </>
      )}
    </div>
  );
}
