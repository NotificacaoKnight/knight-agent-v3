import React, { useState, useRef, useEffect } from 'react';
import { MainLayout } from '../components/MainLayout';
import { 
  ArrowUp, 
  Bot, 
  User, 
  Loader2,
  Mic,
  MicOff,
  Square,
  Play,
  Pause,
  Volume2,
  Trash2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import toast from 'react-hot-toast';
import { useAudioRecording } from '../hooks/useAudioRecording';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  audioBlob?: Blob | null;
  transcription?: string;
  isAudioMessage?: boolean;
  audioDuration?: number;
}

// Componente para mensagem de áudio
const AudioMessage: React.FC<{ message: Message }> = ({ message }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(message.audioDuration || 0);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (message.audioBlob && !audioUrlRef.current) {
      audioUrlRef.current = URL.createObjectURL(message.audioBlob);
      console.log('🎵 URL de áudio criada:', audioUrlRef.current);
    }

    // Só limpar quando o componente for realmente desmontado
    return () => {
      if (audioUrlRef.current) {
        console.log('🗑️ Limpando URL de áudio:', audioUrlRef.current);
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    };
  }, [message.audioBlob]);

  const togglePlay = () => {
    if (!audioUrlRef.current) {
      console.error('❌ URL de áudio não disponível');
      return;
    }

    if (!audioRef.current) {
      console.log('🎵 Criando novo elemento Audio com URL:', audioUrlRef.current);
      audioRef.current = new Audio(audioUrlRef.current);
      
      audioRef.current.addEventListener('loadedmetadata', () => {
        console.log('📊 Metadata carregada, duração:', audioRef.current?.duration);
        const audioDuration = audioRef.current?.duration || 0;
        if (isFinite(audioDuration) && !isNaN(audioDuration)) {
          setDuration(audioDuration);
        }
      });
      
      audioRef.current.addEventListener('timeupdate', () => {
        setCurrentTime(audioRef.current?.currentTime || 0);
      });
      
      audioRef.current.addEventListener('ended', () => {
        console.log('⏹️ Áudio terminou');
        setIsPlaying(false);
        setCurrentTime(0);
      });
      
      audioRef.current.addEventListener('error', (e) => {
        console.error('❌ Erro no áudio:', e);
        setIsPlaying(false);
      });
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      console.log('▶️ Iniciando reprodução');
      audioRef.current.play().catch(error => {
        console.error('❌ Erro ao reproduzir áudio:', error);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    }
  };

  const formatTime = (time: number): string => {
    if (!isFinite(time) || isNaN(time)) {
      return '0:00';
    }
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Se não há audioBlob, não renderizar o player
  if (!message.audioBlob) {
    return (
      <div className="text-sm text-gray-600 dark:text-gray-400 italic">
        Áudio não disponível
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-2">
      {/* Mini player de áudio */}
      <div className="flex items-center space-x-3 bg-blue-500 rounded-lg p-3 min-w-0 max-w-xs">
        <button
          onClick={togglePlay}
          className="flex-shrink-0 p-1.5 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
        >
          {isPlaying ? (
            <Pause className="h-3 w-3" />
          ) : (
            <Play className="h-3 w-3 ml-0.5" />
          )}
        </button>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-1.5 mb-1">
            <Volume2 className="h-3 w-3 text-white/80" />
            <span className="text-xs text-white/90 font-medium">Mensagem de voz</span>
          </div>
          
          {/* Barra de progresso */}
          <div className="relative bg-white/20 rounded-full h-1">
            <div 
              className="absolute top-0 left-0 h-full bg-white rounded-full transition-all duration-100"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          
          <div className="flex justify-between text-xs text-white/80 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{duration > 0 ? formatTime(duration) : '--:--'}</span>
          </div>
        </div>
      </div>
      
      {/* Transcrição */}
      {message.transcription && (
        <div className={`text-xs italic rounded px-2 py-1 ${
          message.transcription === 'Áudio vazio' 
            ? 'text-white/60 bg-white/5' 
            : 'text-white/90 bg-white/10'
        }`}>
          {message.transcription === 'Áudio vazio' ? (
            message.transcription
          ) : (
            `"${message.transcription}"`
          )}
        </div>
      )}
    </div>
  );
};

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Hook para gravação de áudio
  const {
    isRecording,
    audioBlob,
    duration,
    startRecording,
    stopRecording,
    clearRecording,
    error: audioError,
  } = useAudioRecording();

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

  // Exibir erros de áudio
  useEffect(() => {
    if (audioError) {
      toast.error(audioError);
    }
  }, [audioError]);

  const handleMicClick = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  const handlePlayAudio = () => {
    if (audioBlob) {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
      audio.onended = () => URL.revokeObjectURL(audioUrl);
    }
  };

  const handleSendAudio = async () => {
    if (!audioBlob || isLoading) return;
    
    // Criar uma cópia independente do blob para a mensagem
    const audioBlobCopy = audioBlob ? new Blob([audioBlob], { type: audioBlob.type }) : null;
    
    // Adicionar mensagem do usuário IMEDIATAMENTE (com placeholder de transcrição)
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: 'Processando áudio...',
      timestamp: new Date(),
      audioBlob: audioBlobCopy,
      transcription: 'Processando áudio...',
      isAudioMessage: true,
      audioDuration: duration,
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    
    try {
      const response = await chatApi.sendAudioMessage(audioBlob, sessionId || undefined);
      
      // Atualizar session_id se for uma nova sessão
      if (!sessionId) {
        setSessionId(response.session_id);
      }
      
      // Verificar se é áudio vazio
      const isEmptyAudio = response.transcription === '[ÁUDIO_VAZIO]';
      const displayTranscription = isEmptyAudio ? 'Áudio vazio ou inválido' : response.transcription;
      
      // Atualizar a mensagem do usuário com a transcrição real
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id 
          ? { ...msg, content: displayTranscription, transcription: displayTranscription }
          : msg
      ));

      // Adicionar resposta do bot
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
      
      // Mostrar transcrição se diferente da entrada
      if (response.transcription) {
        toast.success(`Áudio transcrito: "${response.transcription.substring(0, 50)}${response.transcription.length > 50 ? '...' : ''}"`);
      }
      
      // Limpar apenas a interface de gravação, mas o blob já foi copiado para a mensagem
      clearRecording();
      
    } catch (error: any) {
      console.error('Erro ao enviar áudio:', error);
      toast.error('Erro ao processar áudio. Tente novamente.');
      
      // Mensagem de erro
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: 'Desculpe, ocorreu um erro ao processar o áudio. Tente novamente.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    const messageContent = inputMessage;
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage({
        message: messageContent,
        session_id: sessionId || undefined,
      });

      // Atualizar session_id se for uma nova sessão
      if (!sessionId) {
        setSessionId(response.session_id);
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
      toast.error('Erro ao enviar mensagem. Tente novamente.');
      
      // Mensagem de erro
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (audioBlob) {
        handleSendAudio();
      } else if (inputMessage.trim()) {
        handleSendMessage();
      }
    }
  };

  return (
    <MainLayout>
      <div className="h-full flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="h-12 w-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Bem-vindo ao Knight Agent!
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Seu assistente IA corporativo está pronto para ajudar.
                  <br />
                  Digite sua mensagem abaixo para começar uma conversa.
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
                          ? 'bg-blue-600 text-white ml-2'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 mr-2'
                      }`}
                    >
                      {message.type === 'user' ? (
                        <User className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>
                    <div
                      className={`${
                        message.type === 'user' && message.isAudioMessage
                          ? 'p-0' // Sem padding para mensagens de áudio
                          : `px-4 py-2 rounded-lg ${
                              message.type === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700'
                            }`
                      }`}
                    >
                      {message.type === 'user' ? (
                        message.isAudioMessage ? (
                          <AudioMessage message={message} />
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
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 mr-2">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="px-4 py-2 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700">
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
            <div className="relative border border-gray-300 dark:border-gray-600 rounded-lg bg-transparent focus-within:border-blue-500 dark:focus-within:border-blue-400 transition-colors">
              {/* Upper section - Text input */}
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Digite sua mensagem..."
                  className="w-full resize-none bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none px-4 pt-3 pb-2 scrollbar-hide"
                  rows={1}
                  style={{ minHeight: '40px', overflowY: 'auto' }}
                />
              </div>
              
              {/* Invisible divider */}
              <div></div>
              
              {/* Bottom section - Features and send button */}
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center space-x-2">
                  {/* Audio recording controls */}
                  {audioBlob ? (
                    // Controles quando há áudio gravado
                    <div className="flex items-center space-x-2">
                      <div className="flex items-center space-x-1 text-sm text-blue-600 dark:text-blue-400 font-medium">
                        <MicOff className="h-3 w-3" />
                        <span>{formatDuration(duration)}</span>
                      </div>
                      <button
                        onClick={handlePlayAudio}
                        className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                        title="Reproduzir áudio"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                      <button
                        onClick={clearRecording}
                        className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                        title="Excluir gravação"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    // Botão de microfone
                    <button
                      onClick={handleMicClick}
                      disabled={isLoading}
                      className={`p-2 rounded-full transition-all duration-200 ${
                        isRecording
                          ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 animate-pulse'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'
                      } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title={isRecording ? `Gravando... ${formatDuration(duration)}` : 'Gravar áudio'}
                    >
                      {isRecording ? (
                        <Square className="h-4 w-4" />
                      ) : (
                        <Mic className="h-4 w-4" />
                      )}
                    </button>
                  )}
                  
                  {/* Mostrar duração durante gravação */}
                  {isRecording && (
                    <div className="text-sm text-red-600 dark:text-red-400 font-mono">
                      {formatDuration(duration)}
                    </div>
                  )}
                </div>
                
                <button
                  onClick={audioBlob ? handleSendAudio : handleSendMessage}
                  disabled={(!inputMessage.trim() && !audioBlob) || isLoading}
                  className={`w-8 h-8 rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm ${
                    (!inputMessage.trim() && !audioBlob) || isLoading
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed opacity-50'
                      : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:scale-105 active:scale-95 dark:hover:shadow-[0_0_20px_rgba(59,130,246,0.3)]'
                  }`}
                  title={audioBlob ? 'Enviar áudio' : 'Enviar mensagem'}
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