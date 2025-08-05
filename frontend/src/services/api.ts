import axios from 'axios';

// Função para determinar a base URL da API
const getApiBaseUrl = () => {
  console.log('🌐 Detectando API URL...', {
    hostname: window.location.hostname,
    env: process.env.REACT_APP_API_URL
  });
  
  // Se estamos no localhost, usar sempre localhost backend
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api';
  }
  
  // Se REACT_APP_API_URL estiver definida, use-a (para tunnel/produção)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL + '/api';
  }
  
  // Para desenvolvimento local, use proxy relativo
  return '/api';
};

// Criar instância do axios com configurações base
const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  // withCredentials removido para evitar problemas com CORS
});

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('sessionToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para lidar com respostas de erro
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expirado ou inválido
      localStorage.removeItem('sessionToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Tipos para a API de chat
export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  context?: any;
  llm_provider?: string;
  response_time?: number;
  content_type?: 'text' | 'audio';
  audio_url?: string;
  audio_duration?: number;
  transcription?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  last_message_at: string;
  is_active: boolean;
}

export interface SendMessageRequest {
  message: string;
  session_id?: string;
  audio_file?: Blob;
  content_type?: 'text' | 'audio';
}

export interface SendMessageResponse {
  message: ChatMessage;
  user_message?: ChatMessage;
  session_id: string;
  context_used: boolean;
  response_time: number;
}

// Funções da API de chat
export const chatApi = {
  // Enviar mensagem
  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    if (data.audio_file) {
      // Para mensagens com áudio, usar FormData
      const formData = new FormData();
      formData.append('message', data.message);
      formData.append('content_type', data.content_type || 'audio');
      formData.append('audio_file', data.audio_file);
      if (data.session_id) {
        formData.append('session_id', data.session_id);
      }
      
      const response = await api.post('/chat/send/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } else {
      // Para mensagens de texto, usar JSON normal
      const response = await api.post('/chat/send/', data);
      return response.data;
    }
  },

  // Criar nova sessão
  newSession: async (): Promise<ChatSession> => {
    const response = await api.post('/chat/sessions/new/');
    return response.data;
  },

  // Listar sessões
  getSessions: async (): Promise<{sessions: ChatSession[]}> => {
    const response = await api.get('/chat/sessions/');
    return response.data;
  },

  // Obter histórico de uma sessão
  getSessionHistory: async (sessionId: string): Promise<{messages: ChatMessage[]}> => {
    const response = await api.get(`/chat/sessions/${sessionId}/history/`);
    return response.data;
  },

  // Deletar sessão
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/chat/sessions/${sessionId}/delete/`);
  },

  // Atualizar título da sessão
  updateSessionTitle: async (sessionId: string, title: string): Promise<ChatSession> => {
    const response = await api.patch(`/chat/sessions/${sessionId}/`, { title });
    return response.data;
  },

  // Submeter feedback
  submitFeedback: async (messageId: string, rating: number, feedback?: string): Promise<void> => {
    await api.post('/chat/feedback/', { message_id: messageId, rating, feedback });
  },

  // Obter estatísticas do chat
  getChatStats: async (): Promise<any> => {
    const response = await api.get('/chat/stats/');
    return response.data;
  },
};

export default api;