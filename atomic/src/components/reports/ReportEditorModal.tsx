import { useEffect, useState, useMemo } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { ScheduleField } from './ScheduleField';
import { ScopeField } from './ScopeField';
import { CitationPolicyField } from './CitationPolicyField';
import { TagSelector } from '../tags/TagSelector';
import {
  useReportsStore,
  Report,
  CitationPolicy,
  ContextScopeMode,
  ContextScopeWindow,
  SourceScopeWindow,
  CreateReportInput,
  UpdateReportInput,
} from '../../stores/reports';
import { Tag } from '../../stores/atoms';
import { useTagsStore } from '../../stores/tags';
import { getBrowserTimeZone } from '../../lib/tz';

interface ReportEditorModalProps {
  isOpen: boolean;
  /// Edit existing report when present; create new when undefined.
  /// Switching between modes between mounts is fine — the form fully
  /// re-derives its state from `report` whenever `isOpen` toggles.
  report?: Report | null;
  /// Pre-fill the create form with these values. Used by the template
  /// gallery to seed name/prompt/schedule from a curated template.
  /// Ignored when `report` is provided (edit mode wins).
  initialBody?: CreateReportInput | null;
  onClose: () => void;
  onSaved?: (report: Report) => void;
}

/// Shared form state for both create and edit. We work in a flat shape
/// matching the Create/UpdateReportInput types so the save path is a
/// near-direct hand-off.
interface FormState {
  name: string;
  description: string;
  research_prompt: string;
  schedule: string;
  schedule_tz: string | null;
  enabled: boolean;
  source_tag_ids: string[];
  source_window: SourceScopeWindow | null;
  context_mode: ContextScopeMode;
  context_tag_ids: string[];
  context_window: ContextScopeWindow | null;
  citation_policy: CitationPolicy;
  output_atom_tags: string[];
}

const DEFAULT_FORM: FormState = {
  name: '',
  description: '',
  research_prompt: '',
  schedule: '0 0 9 * * *', // sensible default: 9am daily
  schedule_tz: null,
  enabled: true,
  source_tag_ids: [],
  source_window: 'since_last_run',
  context_mode: 'same_as_source',
  context_tag_ids: [],
  context_window: null,
  citation_policy: 'source_only',
  output_atom_tags: [],
};

function reportToForm(r: Report): FormState {
  return {
    name: r.name,
    description: r.description ?? '',
    research_prompt: r.research_prompt,
    schedule: r.schedule,
    schedule_tz: r.schedule_tz,
    enabled: r.enabled,
    source_tag_ids: r.source_scope_tag_ids,
    source_window: r.source_scope_window,
    context_mode: r.context_scope_mode,
    context_tag_ids: r.context_scope_tag_ids,
    context_window: r.context_scope_window,
    citation_policy: r.citation_policy,
    output_atom_tags: r.output_atom_tags,
  };
}

function formToCreateInput(f: FormState): CreateReportInput {
  return {
    name: f.name.trim(),
    description: f.description.trim() || null,
    research_prompt: f.research_prompt,
    schedule: f.schedule,
    schedule_tz: f.schedule_tz,
    enabled: f.enabled,
    source_scope_tag_ids: f.source_tag_ids,
    source_scope_window: f.source_window,
    context_scope_mode: f.context_mode,
    // Tag list is only meaningful in explicit mode. The backend
    // ignores it otherwise; we send [] to keep the payload tidy.
    context_scope_tag_ids: f.context_mode === 'explicit' ? f.context_tag_ids : [],
    // The same-as-source mode reuses the source window; sending null
    // is the right shape. Other modes carry their own window.
    context_scope_window: f.context_mode === 'same_as_source' ? null : f.context_window,
    citation_policy: f.citation_policy,
    output_atom_tags: f.output_atom_tags,
  };
}

function formToUpdateInput(f: FormState, original: Report): UpdateReportInput {
  // Send only fields that actually changed. Keeps the merge surface
  // small and avoids accidentally stomping fields the user didn't touch.
  const out: UpdateReportInput = {};
  const trimmedDesc = f.description.trim() || null;
  if (f.name.trim() !== original.name) out.name = f.name.trim();
  if (trimmedDesc !== (original.description ?? null)) out.description = trimmedDesc;
  if (f.research_prompt !== original.research_prompt) out.research_prompt = f.research_prompt;
  if (f.schedule !== original.schedule) out.schedule = f.schedule;
  if (f.schedule_tz !== original.schedule_tz) out.schedule_tz = f.schedule_tz;
  if (f.enabled !== original.enabled) out.enabled = f.enabled;
  if (!sameStringArr(f.source_tag_ids, original.source_scope_tag_ids)) out.source_scope_tag_ids = f.source_tag_ids;
  if (!sameWindow(f.source_window, original.source_scope_window)) out.source_scope_window = f.source_window;
  if (f.context_mode !== original.context_scope_mode) out.context_scope_mode = f.context_mode;
  const ctxTags = f.context_mode === 'explicit' ? f.context_tag_ids : [];
  if (!sameStringArr(ctxTags, original.context_scope_tag_ids)) out.context_scope_tag_ids = ctxTags;
  const ctxWindow = f.context_mode === 'same_as_source' ? null : f.context_window;
  if (!sameWindow(ctxWindow, original.context_scope_window)) out.context_scope_window = ctxWindow;
  if (f.citation_policy !== original.citation_policy) out.citation_policy = f.citation_policy;
  if (!sameStringArr(f.output_atom_tags, original.output_atom_tags)) out.output_atom_tags = f.output_atom_tags;
  return out;
}

function sameStringArr(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

/// Structural equality across both window flavors. The two wire shapes
/// are isomorphic (string variant or `{duration}` object), so one
/// comparator handles source and context.
type AnyScopeWindow = SourceScopeWindow | ContextScopeWindow;

function sameWindow(a: AnyScopeWindow | null, b: AnyScopeWindow | null): boolean {
  if (a === null && b === null) return true;
  if (a === null || b === null) return false;
  if (typeof a === 'string' && typeof b === 'string') return a === b;
  if (typeof a === 'object' && typeof b === 'object') return a.duration === b.duration;
  return false;
}

function createInputToForm(input: CreateReportInput): FormState {
  // Mirror reportToForm but accept the unsaved CreateReportInput shape
  // the template gallery hands us. Fields are nearly identical to the
  // saved Report shape; only the cache fields are absent, which is
  // fine because the editor doesn't read those.
  return {
    name: input.name,
    description: input.description ?? '',
    research_prompt: input.research_prompt,
    schedule: input.schedule,
    schedule_tz: input.schedule_tz ?? null,
    enabled: input.enabled ?? true,
    source_tag_ids: input.source_scope_tag_ids ?? [],
    source_window: input.source_scope_window ?? null,
    context_mode: input.context_scope_mode ?? 'same_as_source',
    context_tag_ids: input.context_scope_tag_ids ?? [],
    context_window: input.context_scope_window ?? null,
    citation_policy: input.citation_policy ?? 'source_only',
    output_atom_tags: input.output_atom_tags ?? [],
  };
}

export function ReportEditorModal({ isOpen, report, initialBody, onClose, onSaved }: ReportEditorModalProps) {
  const create = useReportsStore(s => s.create);
  const update = useReportsStore(s => s.update);
  const tags = useTagsStore(s => s.tags);

  const isEdit = Boolean(report);

  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Re-derive form state every time the modal opens. Three modes:
  //   - `report` set         → edit existing
  //   - `initialBody` set    → create with template prefill
  //   - neither              → create blank with browser tz
  useEffect(() => {
    if (!isOpen) return;
    if (report) {
      setForm(reportToForm(report));
    } else if (initialBody) {
      // Use the template body verbatim, but substitute the browser's
      // tz if the template left it null so the user sees their local
      // wall clock in the schedule preview.
      setForm({
        ...createInputToForm(initialBody),
        schedule_tz: initialBody.schedule_tz ?? getBrowserTimeZone(),
      });
    } else {
      setForm({ ...DEFAULT_FORM, schedule_tz: getBrowserTimeZone() });
    }
    // Auto-expand advanced when:
    //   - editing a report with non-default advanced fields, OR
    //   - prefilling from a template that customizes any advanced field
    // (the latter is the contradiction-scan / open-questions case —
    // users opening those should see why they're configured the way
    // they are)
    const hasAdvancedFromReport = Boolean(report && (
      report.source_scope_tag_ids.length > 0 ||
      report.context_scope_mode !== 'same_as_source' ||
      report.citation_policy !== 'source_only' ||
      report.output_atom_tags.length > 0
    ));
    const hasAdvancedFromBody = Boolean(initialBody && (
      (initialBody.source_scope_tag_ids?.length ?? 0) > 0 ||
      (initialBody.context_scope_mode ?? 'same_as_source') !== 'same_as_source' ||
      (initialBody.citation_policy ?? 'source_only') !== 'source_only' ||
      (initialBody.output_atom_tags?.length ?? 0) > 0
    ));
    setShowAdvanced(hasAdvancedFromReport || hasAdvancedFromBody);
  }, [isOpen, report, initialBody]);

  // Output-tags Tag[] derivation (TagSelector wants Tag objects).
  const outputTagObjs = useMemo<Tag[]>(() => {
    const flat: Tag[] = [];
    function walk(nodes: any[]) {
      for (const n of nodes) {
        flat.push({ id: n.id, name: n.name, parent_id: n.parent_id ?? null, created_at: n.created_at ?? '' });
        if (n.children) walk(n.children);
      }
    }
    walk(tags as any);
    const set = new Set(form.output_atom_tags);
    return flat.filter(t => set.has(t.id));
  }, [tags, form.output_atom_tags]);

  const nameInvalid = form.name.trim().length === 0;
  const promptInvalid = form.research_prompt.trim().length === 0;
  const canSave = !nameInvalid && !promptInvalid && !isSaving;

  const handleSave = async () => {
    if (!canSave) return;
    setIsSaving(true);
    try {
      if (report) {
        const patch = formToUpdateInput(form, report);
        // No-op shortcut: nothing changed. Close without a request.
        if (Object.keys(patch).length === 0) {
          onClose();
          return;
        }
        const merged = await update(report.id, patch);
        onSaved?.(merged);
      } else {
        const created = await create(formToCreateInput(form));
        onSaved?.(created);
      }
      onClose();
    } catch {
      // Store already toasted; keep the modal open so the user can
      // correct what went wrong.
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit "${report?.name ?? ''}"` : 'New Report'}
      width="xl"
      confirmLabel={isEdit ? 'Save changes' : 'Create report'}
      onConfirm={handleSave}
      confirmDisabled={!canSave}
    >
      <div className="flex flex-col gap-5">
        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Name
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="Daily Briefing, Weekly contradiction scan…"
            className={`
              px-3 py-2 rounded-md text-sm
              bg-[var(--color-bg-input)] border border-[var(--color-border)]
              text-[var(--color-text-primary)]
              focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]
              ${nameInvalid && form.name.length > 0 ? 'border-red-500/60' : ''}
            `}
            autoFocus={!isEdit}
            maxLength={120}
          />
        </div>

        {/* Prompt */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
            Research prompt
          </label>
          <textarea
            value={form.research_prompt}
            onChange={(e) => setForm(f => ({ ...f, research_prompt: e.target.value }))}
            placeholder="What is this report supposed to do? E.g. 'Summarize today's AI articles, calling out contradictions with prior coverage.'"
            rows={5}
            className={`
              px-3 py-2 rounded-md text-sm font-mono leading-relaxed resize-y
              bg-[var(--color-bg-input)] border border-[var(--color-border)]
              text-[var(--color-text-primary)]
              focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]
              ${promptInvalid && form.research_prompt.length > 0 ? 'border-red-500/60' : ''}
            `}
          />
          <span className="text-[11px] text-[var(--color-text-tertiary)]">
            The agent reads this verbatim. Be specific about scope, tone, and what counts as a citation.
          </span>
        </div>

        {/* Schedule */}
        <ScheduleField
          cron={form.schedule}
          tz={form.schedule_tz}
          onChange={(cron, tz) => setForm(f => ({ ...f, schedule: cron, schedule_tz: tz }))}
        />

        {/* Enabled */}
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => setForm(f => ({ ...f, enabled: e.target.checked }))}
            className="accent-[var(--color-accent)]"
          />
          <span className="text-[var(--color-text-primary)]">Enabled</span>
          <span className="text-[11px] text-[var(--color-text-tertiary)]">
            (paused reports keep their schedule but don't run)
          </span>
        </label>

        {/* Advanced expander */}
        <button
          type="button"
          onClick={() => setShowAdvanced(s => !s)}
          className="
            self-start flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.1em]
            text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors
          "
        >
          {showAdvanced ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          Advanced
        </button>

        {showAdvanced && (
          <div className="flex flex-col gap-5 pl-3 border-l border-[var(--color-border)]">
            {/* Source scope. ScopeField's broader output union covers
                both source and context wire shapes; for source it can
                only emit `null | 'since_last_run' | {duration}`, all of
                which are valid SourceScopeWindow values. Cast narrows
                the type at the boundary. */}
            <ScopeField
              label="Source scope"
              tagIds={form.source_tag_ids}
              window={form.source_window}
              onChange={(ids, w) => setForm(f => ({
                ...f,
                source_tag_ids: ids,
                source_window: w as SourceScopeWindow | null,
              }))}
            />

            {/* Context scope: same-as-source / all / explicit. The
                backend has three variants, no `None` — "no context" is
                expressed as `explicit` with an empty tag list. */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
                Context scope
              </label>
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    checked={form.context_mode === 'same_as_source'}
                    onChange={() => setForm(f => ({ ...f, context_mode: 'same_as_source' }))}
                    className="accent-[var(--color-accent)]"
                  />
                  <span>Same as source</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    checked={form.context_mode === 'all'}
                    onChange={() => setForm(f => ({ ...f, context_mode: 'all' }))}
                    className="accent-[var(--color-accent)]"
                  />
                  <span>All atoms</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    checked={form.context_mode === 'explicit'}
                    onChange={() => setForm(f => ({ ...f, context_mode: 'explicit' }))}
                    className="accent-[var(--color-accent)]"
                  />
                  <span>Specific tags</span>
                </label>
              </div>
              {form.context_mode === 'explicit' && (
                /* Context scope. hideSinceLastRun=true restricts the
                   output to `null | {duration}`, both valid
                   ContextScopeWindow values. */
                <ScopeField
                  label="Context tags"
                  tagIds={form.context_tag_ids}
                  window={form.context_window}
                  onChange={(ids, w) => setForm(f => ({
                    ...f,
                    context_tag_ids: ids,
                    context_window: w as ContextScopeWindow | null,
                  }))}
                  hideSinceLastRun
                />
              )}
            </div>

            {/* Citation policy */}
            <CitationPolicyField
              value={form.citation_policy}
              onChange={(next) => setForm(f => ({ ...f, citation_policy: next }))}
            />

            {/* Output tags */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium uppercase tracking-[0.1em] text-[var(--color-text-tertiary)]">
                Output tags
                <span className="ml-2 normal-case text-[10px] tracking-normal text-[var(--color-text-tertiary)]">
                  applied to each finding atom
                </span>
              </label>
              <TagSelector
                selectedTags={outputTagObjs}
                onTagsChange={(next) => setForm(f => ({ ...f, output_atom_tags: next.map(t => t.id) }))}
                excludeAutotagTargets
              />
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
