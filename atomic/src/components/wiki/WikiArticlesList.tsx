import { useState } from 'react';
import { BookOpen, Plus } from 'lucide-react';
import { useWikiStore } from '../../stores/wiki';
import { WikiArticleCard } from './WikiArticleCard';
import { NewWikiModal } from './NewWikiModal';

export function WikiArticlesList() {
  const articles = useWikiStore(s => s.articles);
  const suggestedArticles = useWikiStore(s => s.suggestedArticles);
  const isLoadingList = useWikiStore(s => s.isLoadingList);
  const error = useWikiStore(s => s.error);
  const openArticle = useWikiStore(s => s.openArticle);
  const openAndGenerate = useWikiStore(s => s.openAndGenerate);
  const currentTagId = useWikiStore(s => s.currentTagId);
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (isLoadingList && articles.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-secondary)]">
        Loading wiki articles...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Scrollable content: articles + suggestions */}
      <div className="flex-1 overflow-y-auto">
        {articles.length === 0 && suggestedArticles.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-[var(--color-bg-card)] flex items-center justify-center">
              <BookOpen className="w-8 h-8 text-[var(--color-text-secondary)]" strokeWidth={2} />
            </div>
            <div>
              <p className="text-[var(--color-text-primary)] font-medium mb-1">No wiki articles yet</p>
              <p className="text-[var(--color-text-secondary)] text-sm">
                Generate a wiki article from your atoms to synthesize knowledge
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Existing Articles */}
            {articles.length > 0 && (
              <div className="divide-y divide-[var(--color-border)]">
                {articles.map((article) => (
                  <WikiArticleCard
                    key={article.id}
                    article={article}
                    isActive={article.tag_id === currentTagId}
                    onClick={() => openArticle(article.tag_id, article.tag_name)}
                  />
                ))}
              </div>
            )}

            {/* Suggested Articles */}
            {suggestedArticles.length > 0 && (
              <div className="border-t border-[var(--color-border)]">
                <div className="px-4 pt-3 pb-1">
                  <h3 className="text-[10px] font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider">
                    Suggested Articles
                  </h3>
                </div>
                <div className="divide-y divide-[var(--color-border)]">
                  {suggestedArticles.map((suggestion) => (
                    <button
                      key={suggestion.tag_id}
                      onClick={() => openAndGenerate(suggestion.tag_id, suggestion.tag_name)}
                      className="w-full group flex items-center justify-between px-4 py-2.5 hover:bg-[var(--color-bg-elevated)] transition-colors text-left"
                    >
                      <div className="min-w-0 flex-1">
                        <span className="text-sm text-[var(--color-text-primary)]">
                          {suggestion.tag_name}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-[var(--color-text-tertiary)]">
                            {suggestion.atom_count} atom{suggestion.atom_count !== 1 ? 's' : ''}
                          </span>
                          {suggestion.mention_count > 0 && (
                            <span className="text-[11px] text-[var(--color-text-tertiary)]">
                              {suggestion.mention_count} mention{suggestion.mention_count !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                        <Plus className="w-4 h-4 text-[var(--color-accent)]" strokeWidth={2} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* New Article button */}
      <div className="px-3 py-2 border-t border-[var(--color-border)] shrink-0">
        <button
          onClick={() => setIsModalOpen(true)}
          className="w-full flex items-center justify-start gap-1.5 px-2 py-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] rounded-md transition-colors"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2} />
          New Article
        </button>
      </div>

      {/* New Wiki Modal */}
      <NewWikiModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
