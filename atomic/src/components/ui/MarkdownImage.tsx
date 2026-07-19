import { useState, useRef, SyntheticEvent } from 'react';
import { Image as ImageIcon, AlertTriangle } from 'lucide-react';

interface MarkdownImageProps {
  src?: string;
  alt?: string;
}

export function MarkdownImage({ src, alt }: MarkdownImageProps) {
  const [status, setStatus] = useState<'loading' | 'loaded' | 'error'>('loading');
  const imgRef = useRef<HTMLImageElement | null>(null);

  const handleLoad = (_e: SyntheticEvent<HTMLImageElement>) => {
    setStatus('loaded');
  };

  const handleError = (e: SyntheticEvent<HTMLImageElement>) => {
    setStatus('error');
    e.currentTarget.style.display = 'none';
  };

  return (
    <span className="markdown-image-wrapper">
      {status === 'loading' && (
        <span className="markdown-image-placeholder">
          <ImageIcon className="w-8 h-8 text-[var(--color-text-tertiary)]" strokeWidth={2} />
        </span>
      )}
      {status === 'error' && (
        <span className="markdown-image-error">
          <AlertTriangle className="w-6 h-6" strokeWidth={2} />
          <span>Failed to load image</span>
        </span>
      )}
      <img
        ref={imgRef}
        src={src}
        alt={alt || ''}
        loading="eager"
        decoding="async"
        onLoad={handleLoad}
        onError={handleError}
        className={status === 'loaded' ? 'markdown-image-loaded' : 'markdown-image-loading'}
      />
    </span>
  );
}
