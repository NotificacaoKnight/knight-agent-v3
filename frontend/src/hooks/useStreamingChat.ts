/**
 * useStreamingChat - Custom hook for handling streaming chat responses
 *
 * Implements Server-Sent Events (SSE) for real-time message streaming
 * from the RAG system with proper error handling and state management.
 */

import { useState, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config';

interface StreamEvent {
  type: 'start' | 'status' | 'search_complete' | 'token' | 'sources' | 'links' | 'documents' | 'done' | 'error' | 'session_created';
  content?: string;
  message?: string;
  data?: any;
  index?: number;
  chunks_found?: number;
  response_time_ms?: number;
  provider?: string;
  total_tokens?: number;
  session_id?: number;
  title?: string;
}

interface UseStreamingChatOptions {
  onStart?: () => void;
  onToken?: (token: string) => void;
  onSources?: (sources: any[]) => void;
  onLinks?: (links: any[]) => void;
  onDocuments?: (documents: any[]) => void;
  onComplete?: (fullResponse: string, metadata: any) => void;
  onError?: (error: string) => void;
  onStatus?: (status: string) => void;
  onSessionCreated?: (sessionId: number, title: string) => void;
}

export const useStreamingChat = (options: UseStreamingChatOptions = {}) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState('');
  const [status, setStatus] = useState('');
  const [sources, setSources] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);
  const accumulatedContentRef = useRef('');

  const sendStreamingMessage = useCallback(async (
    query: string,
    sessionId?: string,
    contextSize: number = 5,
    maxTokens: number = 1000,
    temperature: number = 0.7,
    language: string = 'pt',
    llmProvider?: string,
    streamDelay: number = 0.03
  ) => {
    // Reset state
    setIsStreaming(true);
    setStreamedContent('');
    setStatus('');
    setSources([]);
    setLinks([]);
    setDocuments([]);
    accumulatedContentRef.current = '';

    // Create abort controller for cancellation
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      // Prepare request body
      const requestBody = {
        query,
        session_id: sessionId ? parseInt(sessionId, 10) : undefined,
        context_size: contextSize,
        max_tokens: maxTokens,
        temperature,
        language,
        llm_provider: llmProvider,
        stream_delay: streamDelay,
      };

      // Make streaming request
      const response = await fetch(`${API_BASE_URL}/api/rag/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for auth
        body: JSON.stringify(requestBody),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Stream not available');
      }

      let buffer = '';

      // Read the stream
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        // Decode the chunk
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: StreamEvent = JSON.parse(line.slice(6));

              switch (data.type) {
                case 'session_created':
                  if (data.session_id) {
                    options.onSessionCreated?.(data.session_id, data.title || '');
                  }
                  break;

                case 'start':
                  setStatus(data.message || 'Iniciando...');
                  options.onStart?.();
                  break;

                case 'status':
                  setStatus(data.message || '');
                  options.onStatus?.(data.message || '');
                  break;

                case 'search_complete':
                  setStatus(`${data.chunks_found || 0} documentos encontrados`);
                  break;

                case 'token':
                  if (data.content) {
                    accumulatedContentRef.current += data.content;
                    setStreamedContent(accumulatedContentRef.current);
                    options.onToken?.(data.content);
                  }
                  break;

                case 'sources':
                  if (data.data) {
                    setSources(data.data);
                    options.onSources?.(data.data);
                  }
                  break;

                case 'links':
                  if (data.data) {
                    setLinks(data.data);
                    options.onLinks?.(data.data);
                  }
                  break;

                case 'documents':
                  if (data.data) {
                    setDocuments(data.data);
                    options.onDocuments?.(data.data);
                  }
                  break;

                case 'done':
                  setIsStreaming(false);
                  setStatus('');

                  const metadata = {
                    response_time_ms: data.response_time_ms,
                    provider: data.provider,
                    total_tokens: data.total_tokens,
                    session_id: data.session_id,
                  };

                  options.onComplete?.(accumulatedContentRef.current, metadata);
                  break;

                case 'error':
                  throw new Error(data.message || 'Erro desconhecido');
              }
            } catch (err) {
              console.error('Error parsing SSE data:', err);
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Streaming cancelled');
      } else {
        console.error('Streaming error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Erro ao enviar mensagem';
        options.onError?.(errorMessage);
      }
    } finally {
      setIsStreaming(false);
      setStatus('');
      abortControllerRef.current = null;
    }
  }, [options]);

  const cancelStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setIsStreaming(false);
    setStatus('');
  }, []);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    cancelStreaming();
  }, [cancelStreaming]);

  return {
    sendStreamingMessage,
    cancelStreaming,
    cleanup,
    isStreaming,
    streamedContent,
    status,
    sources,
    links,
    documents,
  };
};

// Alternative hook for simpler usage with automatic message accumulation
export const useSimpleStreamingChat = () => {
  const [messages, setMessages] = useState<Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: any[];
    links?: any[];
    documents?: any[];
    metadata?: any;
  }>>([]);

  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<{
    content: string;
    sources?: any[];
    links?: any[];
    documents?: any[];
  } | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState('');

  const {
    sendStreamingMessage: sendStream,
    cancelStreaming,
    cleanup,
    isStreaming,
    status,
  } = useStreamingChat({
    onStart: () => {
      setIsLoading(true);
      setCurrentStreamingMessage({ content: '' });
    },
    onToken: (token) => {
      setCurrentStreamingMessage(prev => ({
        ...prev!,
        content: (prev?.content || '') + token
      }));
    },
    onSources: (sources) => {
      setCurrentStreamingMessage(prev => ({
        ...prev!,
        sources
      }));
    },
    onLinks: (links) => {
      setCurrentStreamingMessage(prev => ({
        ...prev!,
        links
      }));
    },
    onDocuments: (documents) => {
      setCurrentStreamingMessage(prev => ({
        ...prev!,
        documents
      }));
    },
    onComplete: (fullResponse, metadata) => {
      const finalMessage = {
        id: Date.now().toString(),
        role: 'assistant' as const,
        content: fullResponse,
        sources: currentStreamingMessage?.sources,
        links: currentStreamingMessage?.links,
        documents: currentStreamingMessage?.documents,
        metadata,
      };

      setMessages(prev => [...prev, finalMessage]);
      setCurrentStreamingMessage(null);
      setIsLoading(false);
    },
    onError: (error) => {
      console.error('Streaming error:', error);
      setCurrentStreamingMessage(null);
      setIsLoading(false);
    },
    onStatus: (status) => {
      setStreamingStatus(status);
    },
  });

  const sendMessage = useCallback(async (content: string, sessionId?: string) => {
    // Add user message
    const userMessage = {
      id: Date.now().toString(),
      role: 'user' as const,
      content,
    };

    setMessages(prev => [...prev, userMessage]);

    // Send streaming request
    await sendStream(content, sessionId);
  }, [sendStream]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentStreamingMessage(null);
  }, []);

  return {
    messages,
    currentStreamingMessage,
    sendMessage,
    clearMessages,
    cancelStreaming,
    cleanup,
    isLoading: isLoading || isStreaming,
    streamingStatus: streamingStatus || status,
  };
};