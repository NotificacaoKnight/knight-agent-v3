import React, { useState, useRef, useEffect } from 'react';
import { MainLayout } from '../components/MainLayout';
import { 
  ArrowUp, 
  Bot, 
  User, 
  Loader2 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import toast from 'react-hot-toast';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
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
                      className={`px-4 py-2 rounded-lg ${
                        message.type === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700'
                      }`}
                    >
                      {message.type === 'user' ? (
                        <p className="text-sm">{message.content}</p>
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
                  onKeyPress={handleKeyPress}
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
                  {/* Space for future features */}
                </div>
                
                <button
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className={`w-8 h-8 rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm ${
                    !inputMessage.trim() || isLoading
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed opacity-50'
                      : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:scale-105 active:scale-95 dark:hover:shadow-[0_0_20px_rgba(59,130,246,0.3)]'
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