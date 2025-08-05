// Custom event for chat session deletion
export const CHAT_SESSION_DELETED_EVENT = 'chatSessionDeleted';

export const emitChatSessionDeleted = (sessionId: string) => {
  const event = new CustomEvent(CHAT_SESSION_DELETED_EVENT, { 
    detail: { sessionId } 
  });
  window.dispatchEvent(event);
};

export const onChatSessionDeleted = (callback: (sessionId: string) => void) => {
  const handler = (event: Event) => {
    const customEvent = event as CustomEvent<{ sessionId: string }>;
    callback(customEvent.detail.sessionId);
  };
  
  window.addEventListener(CHAT_SESSION_DELETED_EVENT, handler);
  
  return () => {
    window.removeEventListener(CHAT_SESSION_DELETED_EVENT, handler);
  };
};