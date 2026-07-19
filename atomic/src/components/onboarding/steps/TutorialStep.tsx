import { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { Button } from '../../ui/Button';
import { useAtomsStore } from '../../../stores/atoms';
import { useTagsStore, type TagWithCount } from '../../../stores/tags';
import { getTransport } from '../../../lib/transport';
import type { OnboardingState, OnboardingAction } from '../useOnboardingState';

function flattenTags(tags: TagWithCount[]): TagWithCount[] {
  const result: TagWithCount[] = [];
  for (const tag of tags) {
    result.push(tag);
    if (tag.children.length > 0) {
      result.push(...flattenTags(tag.children));
    }
  }
  return result;
}

const TUTORIAL_CONTENT = `# Welcome to Atomic

Atomic is your personal knowledge base — a place to capture, connect, and explore ideas using AI.

## Core Concepts

### Atoms
Atoms are the fundamental building blocks. Each atom is a markdown note that gets automatically processed: chunked into semantic segments, embedded as vectors, and (optionally) tagged by AI. This atom you're reading is itself an atom!

### Tags
Tags organize your atoms into a hierarchical tree. When auto-tagging is enabled, AI extracts relevant topics, people, locations, organizations, and events from your notes. You can also add tags manually.

### Semantic Search
Every atom is embedded as a vector, enabling powerful semantic search. Search by meaning, not just keywords — find related ideas even when they use different words.

### Wiki Articles
Select a tag and generate a wiki article that synthesizes all atoms under it. Wiki articles include inline citations back to source atoms, and can be incrementally updated as new content arrives.

### Chat
The chat interface is an agentic RAG system. Scope conversations to specific tags, and the AI agent will search your knowledge base to ground its responses in your actual notes.

### Canvas
The canvas is a spatial visualization of your knowledge graph. Atoms are positioned using force simulation — atoms sharing tags are linked, and semantically similar atoms cluster together. Drag atoms around and positions persist across sessions.

## Getting Started

Here are some things to try:

- **Create a note**: Click the + button or press Cmd+N to create your first atom
- **Search**: Press / to open the command palette and search across all your notes
- **Filter by tag**: Click a tag in the left panel to filter your view
- **Switch views**: Toggle between Canvas, Grid, and List views in the top bar
- **Generate a wiki**: Select a tag and click "Generate Wiki" to synthesize your notes

## Integrations

Atomic connects to your workflow through multiple channels:

- **Browser Extension**: Save web pages to your knowledge base with one click
- **MCP Server**: Let Claude Desktop search your notes during conversations
- **Mobile App**: Read and create atoms on the go with the iOS app
- **RSS Feeds**: Automatically import articles from your favorite sources

Happy knowledge building!
`;

interface TutorialStepProps {
  state: OnboardingState;
  dispatch: React.Dispatch<OnboardingAction>;
}

export function TutorialStep({ state, dispatch }: TutorialStepProps) {
  const createAtom = useAtomsStore(s => s.createAtom);
  const fetchTags = useTagsStore(s => s.fetchTags);
  const [tagNames, setTagNames] = useState<string[]>([]);

  // Subscribe to embedding/tagging events for the tutorial atom
  useEffect(() => {
    if (!state.tutorialAtomId) return;

    const transport = getTransport();
    const atomId = state.tutorialAtomId;

    const unsubEmbed = transport.subscribe<{ atom_id: string; status: string }>('embedding-complete', (payload) => {
      if (payload.atom_id === atomId && payload.status === 'complete') {
        dispatch({ type: 'SET_TUTORIAL_EMBEDDING_DONE', value: true });
      }
    });

    const unsubTag = transport.subscribe<{ atom_id: string; status: string; tags_extracted: string[] }>('tagging-complete', (payload) => {
      if (payload.atom_id === atomId && (payload.status === 'complete' || payload.status === 'skipped')) {
        const tagIds = payload.tags_extracted || [];
        dispatch({ type: 'SET_TUTORIAL_TAGGING_DONE', value: true, tags: tagIds });
      }
    });

    return () => {
      unsubEmbed();
      unsubTag();
    };
  }, [state.tutorialAtomId, dispatch]);

  // Resolve tag IDs to names once tagging completes
  useEffect(() => {
    if (!state.tutorialTaggingDone || state.tutorialTagsExtracted.length === 0) return;

    fetchTags().then(() => {
      const allTags = useTagsStore.getState().tags;
      const flatTags = flattenTags(allTags);
      const names = state.tutorialTagsExtracted
        .map(id => flatTags.find(t => t.id === id)?.name)
        .filter((n): n is string => !!n);
      setTagNames(names);
    });
  }, [state.tutorialTaggingDone, state.tutorialTagsExtracted, fetchTags]);

  const handleCreate = async () => {
    dispatch({ type: 'SET_TUTORIAL_CREATING', value: true });
    try {
      const atom = await createAtom(TUTORIAL_CONTENT);
      dispatch({ type: 'SET_TUTORIAL_ATOM_ID', id: atom.id });
    } catch (e) {
      console.error('Failed to create tutorial atom:', e);
    } finally {
      dispatch({ type: 'SET_TUTORIAL_CREATING', value: false });
    }
  };

  return (
    <div className="space-y-5 px-2">
      <div className="text-center mb-4">
        <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-1">Tutorial Atom</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Create a tutorial note to see the full pipeline in action
        </p>
      </div>

      {!state.tutorialAtomId ? (
        <div className="flex flex-col items-center space-y-4">
          <div className="p-4 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg text-center space-y-3 w-full">
            <p className="text-sm text-[var(--color-text-secondary)]">
              This will create a "Welcome to Atomic" note that covers all the core concepts. Watch as it gets automatically chunked, embedded, and tagged in real time.
            </p>
            <Button onClick={handleCreate} disabled={state.tutorialCreating}>
              {state.tutorialCreating ? 'Creating...' : 'Create Tutorial Atom'}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Status indicators */}
          <div className="p-4 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg space-y-3">
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">Processing Pipeline</h3>

            <div className="space-y-2">
              {/* Atom created */}
              <StatusItem label="Atom created" done={true} />

              {/* Embedding */}
              <StatusItem label="Embedding generated" done={state.tutorialEmbeddingDone} />

              {/* Tagging */}
              <StatusItem label="Tags extracted" done={state.tutorialTaggingDone} />
            </div>
          </div>

          {/* Extracted tags */}
          {state.tutorialTaggingDone && tagNames.length > 0 && (
            <div className="p-4 bg-[var(--color-bg-card)] border border-[var(--color-border)] rounded-lg space-y-2">
              <h3 className="text-sm font-medium text-[var(--color-text-primary)]">Extracted Tags</h3>
              <div className="flex flex-wrap gap-2">
                {tagNames.map((name) => (
                  <span
                    key={name}
                    className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-accent)]/10 text-[var(--color-accent)] border border-[var(--color-accent)]/20"
                  >
                    {name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {state.tutorialEmbeddingDone && state.tutorialTaggingDone && (
            <div className="text-center text-sm text-green-500">
              All done! Your tutorial atom is ready.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusItem({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-3">
      {done ? (
        <div className="w-5 h-5 rounded-full bg-green-500/10 flex items-center justify-center">
          <Check className="w-3.5 h-3.5 text-green-500" strokeWidth={2} />
        </div>
      ) : (
        <div className="w-5 h-5 flex items-center justify-center">
          <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-secondary)]" strokeWidth={2} />
        </div>
      )}
      <span className={`text-sm ${done ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)]'}`}>
        {label}
      </span>
    </div>
  );
}
