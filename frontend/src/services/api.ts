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
  withCredentials: true, // OBRIGATÓRIO para HttpOnly cookies
});

// Helper function to validate JWT token format
const isValidJWT = (token: string): boolean => {
  if (!token || typeof token !== 'string') return false;
  const parts = token.split('.');
  return parts.length === 3 && parts.every(part => part.length > 0);
};

// Interceptor para adicionar token de autenticação e debug
api.interceptors.request.use(
  (config) => {
    console.log('📤 API Request:', config.method?.toUpperCase(), config.url);

    // Adicionar token de autenticação se disponível
    const token = localStorage.getItem('sessionToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('🔑 Token adicionado ao header Authorization');
    } else {
      console.log('⚠️ Nenhum token encontrado no localStorage');
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
      // Token expirado ou inválido (cookies são limpos automaticamente pelo backend)
      console.log('🚨 Erro 401 - Token inválido ou expirado, redirecionando...');

      // Only redirect if not already on login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
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
  agent_type?: string;
  agent_emoji?: string;
  useful_links?: Array<{
    id: number;
    title: string;
    url: string;
    description?: string;
    category: string;
  }>;
  downloadable_documents?: Array<{
    id: number;
    title: string;
    description?: string;
    file_name: string;
    file_type: string;
    file_size: number;
    category: string;
  }>;
}

// Funções da API de chat
export const chatApi = {
  // Enviar mensagem
  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    // Mapear para o formato esperado pelo backend
    const backendPayload = {
      query: data.message,  // backend espera 'query', não 'message'
      session_id: data.session_id ? parseInt(data.session_id) : null,  // converter para number
      use_rag: true,
      use_agentic: false,
      stream: false,
      language: 'pt',
      max_tokens: 1000,
      temperature: 0.7
    };

    if (data.audio_file) {
      // Para mensagens com áudio, usar FormData
      const formData = new FormData();
      formData.append('query', data.message);  // usar 'query' em vez de 'message'
      formData.append('session_id', data.session_id || '');
      formData.append('use_rag', 'true');
      formData.append('use_agentic', 'false');
      formData.append('language', 'pt');
      formData.append('audio_file', data.audio_file);

      const response = await api.post('/chat/query', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } else {
      // Para mensagens de texto, usar JSON normal
      const response = await api.post('/chat/query', backendPayload);
      return response.data;
    }
  },

  // Criar nova sessão
  newSession: async (): Promise<ChatSession> => {
    const response = await api.post('/chat/sessions');
    return response.data;
  },

  // Listar sessões
  getSessions: async (): Promise<{sessions: ChatSession[]}> => {
    const response = await api.get('/chat/sessions');
    return response.data;
  },

  // Obter histórico de uma sessão
  getSessionHistory: async (sessionId: string): Promise<{messages: ChatMessage[]}> => {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  // Deletar sessão
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  // Atualizar título da sessão
  updateSessionTitle: async (sessionId: string, title: string): Promise<ChatSession> => {
    const response = await api.put(`/chat/sessions/${sessionId}/title`, { title });
    return response.data;
  },

  // Submeter feedback
  submitFeedback: async (messageId: string, rating: number, feedback?: string): Promise<void> => {
    await api.post('/chat/feedback', { message_id: messageId, rating, feedback });
  },

  // Obter estatísticas do chat
  getChatStats: async (): Promise<any> => {
    const response = await api.get('/chat/stats');
    return response.data;
  },

  // Download de documentos
  async downloadDocument(documentId: number) {
    const response = await api.get(`/knowledge/documents/${documentId}/download`, {
      responseType: 'blob' // Importante para download de arquivos
    });
    return response;
  },
};

export default api;