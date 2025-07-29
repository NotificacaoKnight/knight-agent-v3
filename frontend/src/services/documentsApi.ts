import api from './api';

// Tipos
interface Document {
  id: number;
  title: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'processed' | 'error';
  processing_error?: string;
  uploaded_at: string;
  processed_at?: string;
  access_count: number;
  is_downloadable: boolean;
}

interface DocumentStats {
  total_documents: number;
  processed_documents: number;
  pending_documents: number;
  processing_documents: number;
  error_documents: number;
  downloadable_documents: number;
  total_chunks: number;
}

interface DocumentContent {
  title: string;
  content: string;
  metadata: any;
  chunks_count: number;
}

interface UploadDocumentData {
  file: File;
  title: string;
  is_downloadable: boolean;
}

export const documentsApi = {
  // Listar documentos
  list: async (): Promise<Document[]> => {
    const response = await api.get('/documents/');
    // Se a resposta tem paginação (DRF), retornar apenas os results
    if (response.data && response.data.results) {
      return response.data.results;
    }
    // Se for array direto, retornar como está
    return Array.isArray(response.data) ? response.data : [];
  },

  // Estatísticas dos documentos
  getStats: async (): Promise<DocumentStats> => {
    const response = await api.get('/documents/stats/');
    return response.data;
  },

  // Upload de documento
  upload: async (data: UploadDocumentData): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', data.file);
    formData.append('title', data.title);
    formData.append('is_downloadable', data.is_downloadable.toString());

    const response = await api.post('/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Obter conteúdo do documento
  getContent: async (documentId: number): Promise<DocumentContent> => {
    const response = await api.get(`/documents/${documentId}/content/`);
    return response.data;
  },

  // Excluir documento
  delete: async (documentId: number): Promise<void> => {
    await api.delete(`/documents/${documentId}/`);
  },

  // Reprocessar documento
  reprocess: async (documentId: number): Promise<void> => {
    await api.post(`/documents/${documentId}/reprocess/`);
  },

  // Download do documento (retorna URL)
  getDownloadUrl: (documentId: number): string => {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    return `${apiUrl}/api/documents/${documentId}/download/`;
  },

  // Buscar chunks do documento
  getChunks: async (documentId: number) => {
    const response = await api.get(`/documents/${documentId}/chunks/`);
    return response.data;
  },

  // Status dos processamentos em andamento
  getProcessingStatus: async () => {
    const response = await api.get('/documents/processing/');
    return response.data;
  },
};