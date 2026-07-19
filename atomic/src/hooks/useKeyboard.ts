import { useEffect } from 'react';

export function useKeyboard(
  key: string,
  handler: () => void,
  enabled: boolean = true,
  ignoreWhenModalOpen: boolean = true
) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if a modal is open (let the modal handle it)
      if (ignoreWhenModalOpen && document.querySelector('[data-modal="true"]')) {
        return;
      }

      if (event.key === key) {
        handler();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [key, handler, enabled, ignoreWhenModalOpen]);
}

