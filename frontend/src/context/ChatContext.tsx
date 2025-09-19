import React, { createContext, useContext, ReactNode, useState, useCallback } from 'react';
import { chatApi } from '../services/api';

interface ChatContextType {
  refreshChatSessions: () => Promise<void>;
  isProcessingMessage: boolean;
  setIsProcessingMessage: (loading: boolean) => void;
  chatSessions: any[];
  setChatSessions: (sessions: any[]) => void;
}

const ChatContext = createContext<ChatContextType | null>(null);

interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [isProcessingMessage, setIsProcessingMessage] = useState(false);
  const [chatSessions, setChatSessions] = useState<any[]>([]);

  const refreshChatSessions = useCallback(async () => {
    try {
      const response = await chatApi.getSessions();
      const sessions = response.sessions;
      const limitedSessions = Array.isArray(sessions) ? sessions.slice(0, 10) : [];
      setChatSessions(limitedSessions);
    } catch (error) {
      console.error('Erro ao atualizar sessões de chat:', error);
      // Set empty array as fallback
      setChatSessions([]);

      // Don't show error to user for chat sessions - just fail silently
      // This prevents UI disruption when authentication is in progress
    }
  }, []);

  const setIsProcessingMessageWithLog = useCallback((value: boolean) => {
    setIsProcessingMessage(value);
  }, []);

  return (
    <ChatContext.Provider value={{ 
      refreshChatSessions, 
      isProcessingMessage, 
      setIsProcessingMessage: setIsProcessingMessageWithLog,
      chatSessions,
      setChatSessions
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
};