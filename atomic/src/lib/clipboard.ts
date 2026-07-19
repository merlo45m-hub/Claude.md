/**
 * Write `text` to the clipboard.
 *
 * Uses the async Clipboard API in secure contexts (HTTPS, Tauri) and falls
 * back to a hidden textarea + `execCommand('copy')` for plain-HTTP localhost,
 * where the Clipboard API is blocked.
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand('copy');
  } finally {
    document.body.removeChild(textarea);
  }
}
