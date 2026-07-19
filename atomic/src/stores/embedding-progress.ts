import { create } from 'zustand';

interface PipelineRemaining {
  embedding: number;
  tagging: number;
}

interface EmbeddingProgressStore {
  embeddingRemaining: number;
  taggingRemaining: number;
  setRemaining: (remaining: PipelineRemaining) => void;
  clear: () => void;
}

export const useEmbeddingProgressStore = create<EmbeddingProgressStore>()((set) => ({
  embeddingRemaining: 0,
  taggingRemaining: 0,

  setRemaining: ({ embedding, tagging }) =>
    set({
      embeddingRemaining: Math.max(0, embedding),
      taggingRemaining: Math.max(0, tagging),
    }),

  clear: () => set({ embeddingRemaining: 0, taggingRemaining: 0 }),
}));
