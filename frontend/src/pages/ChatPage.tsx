import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { MainLayout } from '../components/MainLayout';
import { useAuth } from '../context/AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';
import { onChatSessionDeleted } from '../utils/events';
import {
  ArrowUp,
  Loader2,
  Mic,
  Square,
  Volume2,
  Link,
  Download,
  FileText,
  ExternalLink
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import toast from 'react-hot-toast';
import { AudioPlayer } from '../components/AudioPlayer';
import { useChatContext } from '../context/ChatContext';
import { KnightIcon } from '../components/KnightIcon';
import { useTranslation } from 'react-i18next';
import { useStreamingChat } from '../hooks/useStreamingChat';

enum LoadingState {
  IDLE = 'idle',
  LOADING_HISTORY = 'loading_history',
  SENDING_MESSAGE = 'sending_message',
  STREAMING = 'streaming'
}

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  audioUrl?: string;
  transcription?: string;
  messageType?: 'text' | 'audio';
  audioDuration?: number;
  isProcessingTranscription?: boolean;
  agent_type?: string;
  agent_emoji?: string;
  usefulLinks?: Array<{
    id: number;
    title: string;
    url: string;
    description?: string;
    category: string;
  }>;
  downloadableDocuments?: Array<{
    id: number;
    title: string;
    description?: string;
    file_name: string;
    file_type: string;
    file_size: number;
    category: string;
  }>;
}

export const ChatPage: React.FC = () => {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>();
  const { refreshChatSessions, setIsProcessingMessage } = useChatContext();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loadingState, setLoadingState] = useState<LoadingState>(LoadingState.IDLE);
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId || null);
  const pendingRequestRef = useRef<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [animationKey, setAnimationKey] = useState(0);
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null);
  const streamingDataRef = useRef<{ links?: any[], documents?: any[] }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isCancellingRef = useRef<boolean>(false);
  const previousUrlSessionIdRef = useRef<string | undefined>(urlSessionId);

  // Memoize messages to prevent unnecessary re-renders
  const memoizedMessages = useMemo(() => messages, [messages]);

  // Loading state helpers
  const isLoading = loadingState !== LoadingState.IDLE;
  const isLoadingHistory = loadingState === LoadingState.LOADING_HISTORY;

  // Initialize streaming hook
  const {
    sendStreamingMessage,
  } = useStreamingChat({
    onSessionCreated: (sessionId, title) => {
      console.log('🆕 Session created:', sessionId, title);
      const newSessionId = String(sessionId);
      setSessionId(newSessionId);
      // Atualizar histórico imediatamente quando sessão é criada
      if (refreshChatSessions) {
        refreshChatSessions();
      }
    },
    onStart: () => {
      console.log('🚀 Streaming started');
      // Bloquear navegação durante geração da resposta
      setIsProcessingMessage(true);

      // Clear previous data
      streamingDataRef.current = {};

      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        isLoading: true,
      };
      setStreamingMessage(assistantMessage);
    },
    onToken: (token) => {
      setStreamingMessage(prev => prev ? {
        ...prev,
        content: prev.content + token,
        isLoading: false,
      } : null);
    },
    onSources: (sources) => {
      console.log('📚 Sources received:', sources);
    },
    onLinks: (links) => {
      console.log('🔗 Links received:', links);
      streamingDataRef.current.links = links;
      setStreamingMessage(prev => prev ? {
        ...prev,
        usefulLinks: links,
      } : null);
    },
    onDocuments: (documents) => {
      console.log('📄 Documents received:', documents);
      streamingDataRef.current.documents = documents;
      setStreamingMessage(prev => prev ? {
        ...prev,
        downloadableDocuments: documents,
      } : null);
    },
    onComplete: (fullResponse, metadata) => {
      console.log('✅ Streaming complete:', metadata);
      console.log('📦 Saved links:', streamingDataRef.current.links);
      console.log('📄 Saved documents:', streamingDataRef.current.documents);

      // Create final message preserving accumulated data
      const finalMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: fullResponse,
        timestamp: new Date(),
        isLoading: false,
        usefulLinks: streamingDataRef.current.links || [],
        downloadableDocuments: streamingDataRef.current.documents || [],
      };

      console.log('✉️ Final message with links:', finalMessage);

      // Add to messages and clear streaming state
      setMessages(prev => [...prev, finalMessage]);
      setStreamingMessage(null);
      setLoadingState(LoadingState.IDLE);
      setIsProcessingMessage(false);

      // Clear the ref for next message
      streamingDataRef.current = {};

      // Update session if needed (fallback case)
      if (!sessionId && metadata.session_id) {
        const newSessionId = String(metadata.session_id);
        setSessionId(newSessionId);
      }

      // Sempre atualizar histórico no final para pegar título atualizado
      if (refreshChatSessions) {
        refreshChatSessions();
      }
    },
    onError: (error) => {
      console.error('❌ Streaming error:', error);
      toast.error(`Erro no streaming: ${error}`);
      setStreamingMessage(null);
      setLoadingState(LoadingState.IDLE);
      setIsProcessingMessage(false);
    },
    onStatus: (status) => {
      console.log('📊 Status:', status);
    },
  });

  // Use static page title
  usePageTitle('Knight - Assistente IA');
  
  // Listen for session deletion events
  useEffect(() => {
    const unsubscribe = onChatSessionDeleted((deletedSessionId) => {
      // If the deleted session is the current one, clear immediately
      if (sessionId === deletedSessionId) {
        setMessages([]);
        setSessionId(null);
        setInputMessage('');
        setLoadingState(LoadingState.IDLE);
        setAnimationKey(prev => prev + 1);
      }
    });
    
    return unsubscribe;
  }, [sessionId]);
  
  // Clear messages immediately when URL changes
  useEffect(() => {
    
    // Clear when going from a session to no session
    if (previousUrlSessionIdRef.current && !urlSessionId) {
      setMessages([]);
      setSessionId(null);
      setInputMessage('');
      setLoadingState(LoadingState.IDLE);
      setAnimationKey(prev => prev + 1);

      // Force a complete reset
      if (pendingRequestRef.current) {
        pendingRequestRef.current = null;
      }
    }
    
    previousUrlSessionIdRef.current = urlSessionId;
  }, [urlSessionId]);

  // Memoize personalized greeting to prevent it from changing on every render
  const personalizedGreeting = useMemo(() => {
    const hour = new Date().getHours();
    const firstName = user?.name?.split(' ')[0] || user?.preferred_name?.split(' ')[0] || t('chatPage.user');

    // Time-based greetings
    let timeGreeting = '';
    if (hour >= 5 && hour < 12) {
      timeGreeting = t('chat.good_morning');
    } else if (hour >= 12 && hour < 18) {
      timeGreeting = t('chat.good_afternoon');
    } else {
      timeGreeting = t('chat.good_evening');
    }

    // Various greeting patterns using translation keys
    const greetingPatterns = [
      t('chat.greeting_time_name', { timeGreeting, firstName }),
      t('chat.greeting_hello', { firstName }),
      t('chat.greeting_hi', { firstName }),
      t('chat.greeting_whats_up', { firstName }),
      t('chat.greeting_whats_new', { firstName }),
      t('chat.greeting_how_help', { firstName }),
      t('chat.greeting_ready_work', { firstName }),
      t('chat.greeting_lets_start', { firstName }),
      t('chat.greeting_time_how_are_you', { timeGreeting, firstName }),
      t('chat.greeting_welcome', { firstName })
    ];

    // Select random greeting
    const randomIndex = Math.floor(Math.random() * greetingPatterns.length);
    return greetingPatterns[randomIndex];
  }, [user?.name, user?.preferred_name, t]); // Include t in dependencies

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.max(40, Math.min(textarea.scrollHeight, 150))}px`;
    }
  }, []);

  // Debounced effect to prevent frequent DOM updates that might affect Edge title behavior
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      adjustTextareaHeight();
    }, 50); // 50ms debounce to reduce frequency of DOM manipulations

    return () => clearTimeout(timeoutId);
  }, [inputMessage, adjustTextareaHeight]);

  // Trigger animation when starting a new conversation
  useEffect(() => {
    if (!urlSessionId && messages.length === 0 && !isLoadingHistory) {
      // Small delay to ensure the component is fully rendered
      const timer = setTimeout(() => {
        setAnimationKey(prev => prev + 1);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [urlSessionId, messages.length, isLoadingHistory]);

  // Reset processing state when navigating to new conversation
  useEffect(() => {
    let isActive = true;

    if (!urlSessionId && isActive) {
      if (process.env.NODE_ENV === 'development') {
        console.log('Resetting isProcessingMessage because no urlSessionId');
      }
      setIsProcessingMessage(false);
    }

    return () => { isActive = false; };
  }, [urlSessionId, setIsProcessingMessage]);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      setIsProcessingMessage(false);
    };
  }, []); // Remove setIsProcessingMessage from deps to avoid unnecessary re-runs


  // Load session history when sessionId from URL changes
  useEffect(() => {
    const loadSessionHistory = async () => {
      // Cancel any pending request when switching sessions
      if (pendingRequestRef.current) {
        pendingRequestRef.current = null;
        setLoadingState(LoadingState.IDLE);
        setIsProcessingMessage(false);
      }

      if (urlSessionId) {
        setLoadingState(LoadingState.LOADING_HISTORY);
        // Title is now static, no need to update
        
        try {
          const historyResponse = await chatApi.getSessionHistory(urlSessionId);
          const historyMessages = historyResponse.messages;
          
          if (Array.isArray(historyMessages)) {
            const convertedMessages: Message[] = historyMessages.map((msg: any) => ({
              id: msg.id.toString(),
              type: msg.message_type as 'user' | 'assistant' | 'system',
              content: msg.content,
              timestamp: new Date(msg.created_at || msg.timestamp),
              messageType: msg.content_type || 'text',
              transcription: msg.transcription,
              audioDuration: msg.audio_duration,
              audioUrl: msg.audio_file ? msg.audio_file : undefined,
              agent_type: msg.agent_type,
              agent_emoji: msg.agent_emoji,
              usefulLinks: msg.useful_links || msg.usefulLinks, // Mapear links úteis
              downloadableDocuments: msg.downloadable_documents || msg.downloadableDocuments, // Mapear documentos
            }));

            setMessages(convertedMessages);
            setSessionId(urlSessionId);
            
            // Title is now static, no need to update
          }
        } catch (error) {
          console.error('Erro ao carregar histórico da sessão:', error);
          toast.error(t('chat.session_load_error'));
          setMessages([]);
        } finally {
          setLoadingState(LoadingState.IDLE);
        }
      } else {
        // Reset for new session
        setMessages([]);
        setSessionId(null);
        setInputMessage('');
        setLoadingState(LoadingState.IDLE);
        // Force re-render of greeting
        setAnimationKey(prev => prev + 1);
      }
    };

    loadSessionHistory();
  }, [urlSessionId, setIsProcessingMessage]);

  // Helper function for regular (non-streaming) message sending
  const sendRegularMessage = useCallback(async (
    messageContent: string,
    userMessage: Message,
    requestId: string,
    audioFile?: Blob | null
  ) => {
    try {
      const response = await chatApi.sendMessage({
        message: messageContent,
        session_id: sessionId || undefined,
        audio_file: audioFile || undefined,
        content_type: audioFile ? 'audio' : 'text',
      });

      // Check if this request is still valid (user hasn't switched sessions)
      if (pendingRequestRef.current !== requestId) {
        console.log('Request cancelled due to session switch');
        return;
      }

      // Atualizar session_id se for uma nova sessão
      if (!sessionId) {
        setSessionId(response.session_id);
        // Refresh chat sessions in sidebar when a new session is created
        if (refreshChatSessions) {
          refreshChatSessions();
        }
        // Title is now static, no need to update
      }

      // Atualizar a mensagem do usuário com transcrição e duração real assim que disponível
      if (response.user_message && response.user_message.content_type === 'audio') {
        console.log('🔄 Updating user message with transcription:', {
          backendDuration: response.user_message.audio_duration,
          originalDuration: userMessage.audioDuration,
          transcription: response.user_message.transcription
        });

        setMessages(prev => prev.map(msg => {
          if (msg.type === 'user' && msg.timestamp.getTime() === userMessage.timestamp.getTime()) {
            // SEMPRE manter a duração original do frontend (mais precisa que a estimativa do backend)
            const finalDuration = msg.audioDuration;

            console.log('🎵 Final duration choice:', {
              backend: response.user_message!.audio_duration,
              original: msg.audioDuration,
              final: finalDuration
            });

            return {
              ...msg,
              transcription: response.user_message!.transcription,
              content: response.user_message!.content,
              audioDuration: finalDuration,
              isProcessingTranscription: false
            };
          }
          return msg;
        }));
      }

      const botMessage: Message = {
        id: response.message.id,
        type: 'assistant',
        content: response.message.content,
        timestamp: new Date(response.message.timestamp),
        agent_type: response.agent_type,
        agent_emoji: response.agent_emoji,
        usefulLinks: response.useful_links,
        downloadableDocuments: response.downloadable_documents,
      };

      setMessages(prev => [...prev, botMessage]);

      if (response.context_used) {
        toast.success(t('chat.response_with_documents'));
      }

    } catch (error: any) {
      console.error('Erro ao enviar mensagem:', error);

      // Extrair mensagem de erro específica se disponível
      let errorContent = t('chat.processing_message_error');
      let toastMessage = t('chat.send_error');

      if (error.response?.data?.message?.content) {
        errorContent = error.response.data.message.content;
        toastMessage = t('chat.processing_error');
      } else if (error.response?.data?.error) {
        // Verificar se é erro de áudio específico
        const apiError = error.response.data.error;
        if (apiError.includes('transcrição')) {
          toastMessage = t('chat.transcription_error');
        } else if (apiError.includes('muito grande')) {
          toastMessage = t('chat.file_too_large');
        } else if (apiError.includes('formato')) {
          toastMessage = t('chat.unsupported_format');
        }
      }

      toast.error(toastMessage);

      // Mensagem de erro
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: errorContent,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      // Always reset processing state, but only reset loading if this is still the current request
      setIsProcessingMessage(false);
      if (pendingRequestRef.current === requestId) {
        setLoadingState(LoadingState.IDLE);
        pendingRequestRef.current = null;
      }
    }
  }, [sessionId, refreshChatSessions, t, setIsProcessingMessage]);

  const handleSendMessage = useCallback(async () => {
    if ((!inputMessage.trim() && !audioBlob) || isLoading) return;

    const isAudioMessage = audioBlob !== null;
    const currentAudioBlob = audioBlob; // Save before clearing
    const requestId = Date.now().toString();
    const userMessage: Message = {
      id: requestId,
      type: 'user',
      content: isAudioMessage
        ? (inputMessage.trim() ? inputMessage : t('chat.audio_message'))
        : inputMessage,
      timestamp: new Date(),
      messageType: isAudioMessage ? 'audio' : 'text',
      audioUrl: isAudioMessage ? URL.createObjectURL(audioBlob) : undefined,
      audioDuration: isAudioMessage ? recordingTime : undefined,
      isProcessingTranscription: isAudioMessage,
    };

    const messageContent = inputMessage;
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setAudioBlob(null);
    setRecordingTime(0);
    setLoadingState(LoadingState.SENDING_MESSAGE);
    pendingRequestRef.current = requestId;

    // Use streaming for text messages, regular mode for audio
    if (!isAudioMessage) {
      try {
        await sendStreamingMessage(
          messageContent,
          sessionId || undefined,
          5,  // context_size
          1000,  // max_tokens
          0.7,  // temperature
          'pt',  // language
          undefined,  // llm_provider
          0.05  // stream_delay - velocidade normal (50ms)
        );
      } catch (error) {
        console.error('Streaming failed, falling back to regular mode:', error);
        // Fallback to regular mode if streaming fails
        await sendRegularMessage(messageContent, userMessage, requestId, currentAudioBlob);
      }
      return;
    }

    // Regular mode for audio messages
    await sendRegularMessage(messageContent, userMessage, requestId, currentAudioBlob);
  }, [inputMessage, audioBlob, isLoading, sessionId, recordingTime, t, sendStreamingMessage, sendRegularMessage]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Só criar audioBlob se não foi cancelado
        if (!isCancellingRef.current) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          setAudioBlob(audioBlob);
        }
        stream.getTracks().forEach(track => track.stop());
        isCancellingRef.current = false; // Reset da flag
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      isCancellingRef.current = false; // Garantir que flag está limpa
      
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Erro ao acessar microfone:', error);
      toast.error('Não foi possível acessar o microfone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
      
      // Nota: Não parar o stream aqui porque o onstop vai criar o audioBlob
      // O stream será parado automaticamente no onstop handler
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      // Marcar como cancelamento antes de parar (usando ref para valor imediato)
      isCancellingRef.current = true;
      
      // Parar gravação (isso vai disparar o onstop, mas não vai criar audioBlob)
      mediaRecorderRef.current.stop();
      
      // Limpar completamente o estado
      setIsRecording(false);
      setAudioBlob(null);
      setRecordingTime(0);
      audioChunksRef.current = [];
      
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
    }
  };

  const formatRecordingTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
    };
  }, []);

  return (
    <MainLayout>
      <div className="h-full flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 custom-scrollbar">
          <div className="max-w-4xl mx-auto space-y-4">
            {isLoadingHistory ? (
              <div className="text-center py-12">
                <Loader2 className="h-8 w-8 text-muted-foreground mx-auto mb-4 animate-spin" />
                <p className="text-muted-foreground">Carregando histórico da conversa...</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="text-center py-16 px-8">
                {urlSessionId ? (
                  <>
                    <KnightIcon className="h-16 w-16 text-muted-foreground mx-auto mb-6" />
                    <h3 className="text-xl font-semibold text-foreground mb-3">
                      Conversa não encontrada
                    </h3>
                    <p className="text-muted-foreground text-base">
                      Esta conversa pode ter sido removida ou você não tem acesso a ela.
                    </p>
                  </>
                ) : (
                  <h3 
                    key={animationKey}
                    className="text-4xl mb-4 animate-fade-in"
                    style={{ 
                      fontFamily: '"Playfair Display", serif',
                      fontWeight: 200,
                      color: 'rgb(var(--foreground-secondary))',
                      textShadow: '0 1px 3px rgba(0, 0, 0, 0.3)',
                      letterSpacing: '0.01em',
                      lineHeight: '1.2',
                      animation: 'fadeIn 1.5s ease-out forwards'
                    }}
                  >
                    {personalizedGreeting}
                  </h3>
                )}
              </div>
            ) : (
              memoizedMessages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`flex max-w-xs lg:max-w-md xl:max-w-lg ${
                      message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                  >
                    {/* Avatar apenas para assistente */}
                    {message.type !== 'user' && (
                      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground mr-2">
                        <span className="text-sm">
                          {message.agent_emoji || '🤖'}
                        </span>
                      </div>
                    )}
                    <div
                      className={`px-4 py-2 rounded-lg ${
                        message.type === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-card text-card-foreground border border-border'
                      }`}
                    >
                      {message.type === 'user' ? (
                        message.messageType === 'audio' && message.audioUrl ? (
                          <AudioPlayer 
                            audioUrl={message.audioUrl} 
                            transcription={message.transcription}
                            initialDuration={message.audioDuration}
                            isProcessingTranscription={message.isProcessingTranscription}
                          />
                        ) : (
                          <p className="text-sm">{message.content}</p>
                        )
                      ) : (
                        <>
                          <div className="text-sm prose dark:prose-invert max-w-none">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                          </div>
                          
                          {/* Renderizar Links Úteis */}
                          {message.usefulLinks && message.usefulLinks.length > 0 && (
                            <div className="mt-4 space-y-2">
                              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                                <Link className="h-3 w-3" />
                                <span>Links Úteis</span>
                              </div>
                              <div className="space-y-1">
                                {message.usefulLinks.map((link) => (
                                  <a
                                    key={link.id}
                                    href={link.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 p-2 text-xs rounded-lg bg-secondary/50 hover:bg-secondary transition-colors group"
                                  >
                                    <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                                    <div className="flex-1">
                                      <div className="font-medium">{link.title}</div>
                                      {link.description && (
                                        <div className="text-muted-foreground line-clamp-1">{link.description}</div>
                                      )}
                                    </div>
                                    <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                                      {link.category}
                                    </span>
                                  </a>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Renderizar Documentos para Download */}
                          {message.downloadableDocuments && message.downloadableDocuments.length > 0 && (
                            <div className="mt-4 space-y-2">
                              <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                                <FileText className="h-3 w-3" />
                                <span>Documentos Disponíveis</span>
                              </div>
                              <div className="space-y-1">
                                {message.downloadableDocuments.map((doc) => (
                                  <button
                                    key={doc.id}
                                    onClick={async () => {
                                      try {
                                        toast.loading('Preparando download...', { id: `download-${doc.id}` });
                                        
                                        const response = await chatApi.downloadDocument(doc.id);
                                        
                                        // Criar blob URL e fazer download
                                        const blob = new Blob([response.data]);
                                        const url = window.URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = doc.file_name || doc.title;
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                        window.URL.revokeObjectURL(url);
                                        
                                        toast.success(`Download de ${doc.file_name} concluído!`, { id: `download-${doc.id}` });
                                      } catch (error) {
                                        console.error('Erro no download:', error);
                                        toast.error('Erro ao baixar o arquivo', { id: `download-${doc.id}` });
                                      }
                                    }}
                                    className="flex items-center gap-2 p-2 w-full text-xs rounded-lg bg-secondary/50 hover:bg-secondary transition-colors group text-left"
                                  >
                                    <Download className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                                    <div className="flex-1">
                                      <div className="font-medium">{doc.title}</div>
                                      {doc.description && (
                                        <div className="text-muted-foreground line-clamp-1">{doc.description}</div>
                                      )}
                                      <div className="text-[10px] text-muted-foreground">
                                        {doc.file_name} • {(doc.file_size / 1024).toFixed(1)} KB
                                      </div>
                                    </div>
                                    <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                                      {doc.file_type.toUpperCase()}
                                    </span>
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Streaming message */}
            {streamingMessage && (
              <div className="flex justify-start">
                <div className="flex max-w-xs lg:max-w-md xl:max-w-lg flex-row">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground mr-2">
                    <span className="text-sm">🤖</span>
                  </div>
                  <div className="px-4 py-2 rounded-lg bg-card text-card-foreground border border-border">
                    {streamingMessage.content ? (
                      <>
                        <div className="text-sm prose dark:prose-invert max-w-none">
                          <ReactMarkdown>{streamingMessage.content}</ReactMarkdown>
                        </div>

                        {/* Render Links if already received */}
                        {streamingMessage.usefulLinks && streamingMessage.usefulLinks.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                              <Link className="h-3 w-3" />
                              <span>Links Úteis</span>
                            </div>
                            <div className="space-y-1">
                              {streamingMessage.usefulLinks.map((link: any) => (
                                <a
                                  key={link.id}
                                  href={link.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-2 p-2 text-xs rounded-lg bg-secondary/50 hover:bg-secondary transition-colors group"
                                >
                                  <ExternalLink className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
                                  <div className="flex-1">
                                    <div className="font-medium">{link.title}</div>
                                    {link.description && (
                                      <div className="text-muted-foreground line-clamp-1">{link.description}</div>
                                    )}
                                  </div>
                                  <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                                    {link.category}
                                  </span>
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex items-center">
                        <span className="animate-pulse">•••</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {isLoading && !streamingMessage && (
              <div className="flex justify-start">
                <div className="flex max-w-xs lg:max-w-md xl:max-w-lg flex-row">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground mr-2">
                    <span className="text-sm">🤖</span>
                  </div>
                  <div className="px-4 py-2 rounded-lg bg-card text-card-foreground border border-border">
                    <div className="flex items-center">
                      <span className="animate-pulse">•••</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="flex-shrink-0 p-4">
          <div className="max-w-4xl mx-auto">
            <div className={`relative border border-border rounded-lg bg-secondary focus-within:border-ring transition-colors ${
              isLoading ? 'opacity-60 pointer-events-none' : ''
            }`}>
              {/* Recording indicator */}
              {isRecording && (
                <div className="absolute -top-12 left-4 right-4 bg-gray-100 text-gray-800 px-3 py-2 rounded-lg flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    <span className="text-sm font-medium">Gravando... {formatRecordingTime(recordingTime)}</span>
                  </div>
                  <button
                    onClick={cancelRecording}
                    className="text-gray-800 hover:bg-gray-200 rounded px-2 py-1 text-sm"
                  >
                    Cancelar
                  </button>
                </div>
              )}

              {/* Audio preview */}
              {audioBlob && !isRecording && (
                <div className="px-4 pt-3 pb-2 border-b border-border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Volume2 className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        Áudio gravado ({formatRecordingTime(recordingTime)})
                      </span>
                    </div>
                    <button
                      onClick={() => {
                        setAudioBlob(null);
                        setRecordingTime(0);
                      }}
                      className="text-muted-foreground hover:text-foreground text-sm"
                    >
                      Remover
                    </button>
                  </div>
                </div>
              )}
              
              {/* Text input */}
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={audioBlob ? "Adicione texto opcional..." : "Digite sua mensagem ou grave um áudio..."}
                  className="w-full resize-none bg-transparent text-foreground placeholder-muted-foreground focus:outline-none px-4 pt-3 pb-2 scrollbar-hide"
                  rows={1}
                  style={{ minHeight: '40px', overflowY: 'auto' }}
                  disabled={isRecording}
                  // Edge-specific attributes to prevent title interference
                  autoComplete="off"
                  data-form-type="other"
                  data-lpignore="true"
                />
              </div>
              
              {/* Bottom section - Audio button, mode buttons and send button */}
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center space-x-2">
                  {/* Audio button */}
                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isLoading}
                    className={`w-8 h-8 rounded-lg transition-all duration-200 flex items-center justify-center ${
                      isRecording
                        ? 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                        : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'
                    }`}
                    title={isRecording ? 'Parar gravação' : 'Gravar áudio'}
                  >
                    {isRecording ? (
                      <Square className="h-4 w-4 fill-current" />
                    ) : (
                      <Mic className="h-4 w-4" />
                    )}
                  </button>
                </div>

                <div className="flex items-center space-x-2">
                  {/* Send button */}
                  <button
                    onClick={handleSendMessage}
                    disabled={(!inputMessage.trim() && !audioBlob) || isLoading || isRecording}
                    className={`w-8 h-8 rounded-lg transition-all duration-200 flex items-center justify-center ${
                      (!inputMessage.trim() && !audioBlob) || isLoading || isRecording
                        ? 'bg-knight-secondary/30 text-knight-secondary/50 cursor-not-allowed shadow-sm'
                        : 'bg-knight-secondary text-gray-700 hover:bg-knight-secondary/90 hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(255,166,0,0.4)]'
                    }`}
                  >
                    <ArrowUp className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};