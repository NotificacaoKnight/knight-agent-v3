import React, { useState, useRef, useEffect } from 'react';
import { MainLayout } from '../components/MainLayout';
import { 
  ArrowUp, 
  Bot, 
  User, 
  Loader2,
  Mic,
  Square,
  Volume2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import toast from 'react-hot-toast';
import { AudioPlayer } from '../components/AudioPlayer';

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
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isCancelling, setIsCancelling] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isCancellingRef = useRef<boolean>(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.max(40, Math.min(textarea.scrollHeight, 150))}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputMessage]);

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && !audioBlob) || isLoading) return;

    const isAudioMessage = audioBlob !== null;
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: isAudioMessage 
        ? (inputMessage.trim() ? inputMessage : 'Mensagem de áudio')
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
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage({
        message: messageContent,
        session_id: sessionId || undefined,
        audio_file: audioBlob || undefined,
        content_type: audioBlob ? 'audio' : 'text',
      });

      // Atualizar session_id se for uma nova sessão
      if (!sessionId) {
        setSessionId(response.session_id);
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
      };

      setMessages(prev => [...prev, botMessage]);
      
      if (response.context_used) {
        toast.success('Resposta baseada em documentos corporativos');
      }
      
    } catch (error: any) {
      console.error('Erro ao enviar mensagem:', error);
      
      // Extrair mensagem de erro específica se disponível
      let errorContent = 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.';
      let toastMessage = 'Erro ao enviar mensagem. Tente novamente.';
      
      if (error.response?.data?.message?.content) {
        errorContent = error.response.data.message.content;
        toastMessage = 'Erro no processamento da mensagem';
      } else if (error.response?.data?.error) {
        // Verificar se é erro de áudio específico
        const apiError = error.response.data.error;
        if (apiError.includes('transcrição')) {
          toastMessage = 'Erro na transcrição do áudio';
        } else if (apiError.includes('muito grande')) {
          toastMessage = 'Arquivo muito grande (máx 20MB)';
        } else if (apiError.includes('formato')) {
          toastMessage = 'Formato de áudio não suportado';
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
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

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
      <div className="h-full flex flex-col bg-background">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Bem-vindo ao Knight Agent!
                </h3>
                <p className="text-muted-foreground">
                  Seu assistente IA corporativo está pronto para ajudar.
                  <br />
                  Digite sua mensagem ou grave um áudio para começar uma conversa.
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`flex max-w-xs lg:max-w-md xl:max-w-lg ${
                      message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                  >
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        message.type === 'user'
                          ? 'bg-primary text-primary-foreground ml-2'
                          : 'bg-muted text-muted-foreground mr-2'
                      }`}
                    >
                      {message.type === 'user' ? (
                        <User className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>
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
                        <div className="text-sm prose dark:prose-invert max-w-none">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex flex-row">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-muted text-muted-foreground mr-2">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="px-4 py-2 rounded-lg bg-card text-card-foreground border border-border">
                    <Loader2 className="h-4 w-4 animate-spin" />
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
            <div className="relative border border-border rounded-lg bg-card focus-within:border-ring transition-colors">
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
                />
              </div>
              
              {/* Bottom section - Audio button and send button */}
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center space-x-2">
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
                
                <button
                  onClick={handleSendMessage}
                  disabled={(!inputMessage.trim() && !audioBlob) || isLoading || isRecording}
                  className={`w-8 h-8 rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm ${
                    (!inputMessage.trim() && !audioBlob) || isLoading || isRecording
                      ? 'bg-muted text-muted-foreground cursor-not-allowed opacity-50'
                      : 'bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95'
                  }`}
                >
                  <ArrowUp className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};