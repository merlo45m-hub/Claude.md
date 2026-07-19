import { useDatabasesStore } from '../../stores/databases';
import { useSettingsStore } from '../../stores/settings';
import { isWorkspaceOnly } from '../../lib/settings';

interface Props {
  /** The settings key this control governs (e.g. `chat_model`). */
  settingKey: string;
}

/**
 * Renders the per-field override affordance — a small chip showing whether
 * the field is using the workspace default or a per-DB override, plus a
 * `Reset` action when overridden.
 *
 * Renders nothing when:
 *   - the workspace has only one database (overrides are meaningless), or
 *   - the key is workspace-only (e.g. theme, API keys — registry-locked).
 *
 * Editing the field while N>1 implicitly creates an override (the resolver
 * routes writes to the per-DB table); the chip flips to "Overridden" via the
 * store's optimistic source update.
 */
export function OverrideControls({ settingKey }: Props) {
  const databases = useDatabasesStore((s) => s.databases);
  const activeId = useDatabasesStore((s) => s.activeId);
  const source = useSettingsStore((s) => s.sources[settingKey]);
  const clearOverride = useSettingsStore((s) => s.clearOverride);

  if (isWorkspaceOnly(settingKey) || databases.length <= 1) {
    return null;
  }

  const activeDbName =
    databases.find((d) => d.id === activeId)?.name ?? 'this database';
  const isOverridden = source === 'override';

  const handleReset = async () => {
    try {
      await clearOverride(settingKey);
    } catch (e) {
      console.error(`Failed to clear override for ${settingKey}:`, e);
    }
  };

  return (
    <div className="mt-1.5 flex items-center justify-between gap-2 text-xs">
      {isOverridden ? (
        <>
          <span
            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-accent)]/40 bg-[var(--color-accent)]/10 px-2 py-0.5 text-[var(--color-accent)]"
            title={`This database overrides the workspace default`}
          >
            Overridden for{' '}
            <span className="font-mono">{activeDbName}</span>
          </span>
          <button
            type="button"
            onClick={handleReset}
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:underline"
          >
            Reset to default
          </button>
        </>
      ) : (
        <span
          className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-card)] px-2 py-0.5 text-[var(--color-text-secondary)]"
          title="Inherited from the workspace default. Editing this field will override it for the active database."
        >
          Workspace default
        </span>
      )}
    </div>
  );
}
