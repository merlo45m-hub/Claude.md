import { useEffect, RefObject } from 'react';

export function useClickOutside(
  ref: RefObject<HTMLElement>,
  handler: () => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;

      // Ignore if clicking inside the ref
      if (ref.current && ref.current.contains(target)) {
        return;
      }

      // Ignore if clicking inside a modal (portaled elements)
      const targetEl = target as HTMLElement;
      if (targetEl.closest?.('[data-modal="true"]')) {
        return;
      }

      handler();
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [ref, handler, enabled]);
}

