import { BookOpen } from 'lucide-react';
import { WikiArticleSummary } from '../../stores/wiki';
import { formatRelativeDate } from '../../lib/date';

interface WikiArticleCardProps {
  article: WikiArticleSummary;
  isActive?: boolean;
  onClick: () => void;
}

export function WikiArticleCard({ article, isActive, onClick }: WikiArticleCardProps) {
  const updatedAt = formatRelativeDate(article.updated_at);

  return (
    <div
      onClick={onClick}
      className={`group px-4 py-3 cursor-pointer transition-colors ${
        isActive
          ? 'bg-[var(--color-accent)]/10'
          : 'hover:bg-[var(--color-bg-card)]'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Tag name as title */}
          <h3 className="text-[var(--color-text-primary)] font-medium truncate mb-1">
            {article.tag_name}
          </h3>

          {/* Meta info */}
          <div className="flex items-center gap-3 text-xs text-[var(--color-text-tertiary)]">
            <span>{updatedAt}</span>
            <span className="text-[var(--color-text-secondary)]">
              {article.atom_count} {article.atom_count === 1 ? 'source' : 'sources'}
            </span>
            {article.inbound_links > 0 && (
              <span className="text-[var(--color-accent-light)]">
                {article.inbound_links} {article.inbound_links === 1 ? 'link' : 'links'}
              </span>
            )}
          </div>
        </div>

        {/* Wiki icon indicator */}
        <div className="p-1.5 text-[var(--color-text-tertiary)]">
          <BookOpen className="w-4 h-4" strokeWidth={2} />
        </div>
      </div>
    </div>
  );
}
