import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useChatStore } from '../../stores/chat';
import { useUIStore } from '../../stores/ui';
import { useDatabasesStore } from '../../stores/databases';
import { ConversationsList } from './ConversationsList';
import { ChatView } from './ChatView';

export function ChatViewer() {
  const view = useChatStore(s => s.view);
  const showList = useChatStore(s => s.showList);
  const openConversation = useChatStore(s => s.openConversation);
  const openOrCreateForTag = useChatStore(s => s.openOrCreateForTag);
  const setChatSidebarOpen = useUIStore(s => s.setChatSidebarOpen);
  const initialTagId = useUIStore(s => s.chatSidebarInitialTagId);
  const initialConversationId = useUIStore(s => s.chatSidebarInitialConversationId);
  const lastConversationId = useUIStore(s => s.chatSidebarConversationId);
  const activeDbId = useDatabasesStore(s => s.activeId);
  const initializedRef = useRef(false);

  // Re-initialize when database changes
  useEffect(() => {
    if (initializedRef.current) {
      showList();
    }
  }, [activeDbId, showList]);

  // Initialize on first mount, and navigate when new initial values are set
  useEffect(() => {
    if (initialConversationId) {
      openConversation(initialConversationId);
      useUIStore.getState().clearChatSidebarInitial();
    } else if (initialTagId) {
      openOrCreateForTag(initialTagId);
      useUIStore.getState().clearChatSidebarInitial();
    } else if (!initializedRef.current) {
      if (lastConversationId) {
        openConversation(lastConversationId);
      } else {
        showList();
      }
    }
    initializedRef.current = true;
  }, [initialTagId, initialConversationId, lastConversationId, showList, openConversation, openOrCreateForTag]);

  return (
    <div className="h-full flex flex-col bg-[var(--color-bg-panel)]">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          {view === 'list' ? 'Conversations' : 'Chat'}
        </h2>
        <button
          onClick={() => setChatSidebarOpen(false)}
          className="p-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          aria-label="Close"
        >
          <X className="w-5 h-5" strokeWidth={2} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {view === 'list' ? <ConversationsList /> : <ChatView />}
      </div>
    </div>
  );
}
