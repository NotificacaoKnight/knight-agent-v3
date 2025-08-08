import api from './api';

// Types
export interface UsefulLink {
  id: number;
  title: string;
  url: string;
  description?: string;
  ai_guidance?: string;
  category: string;
  is_active: boolean;
  send_count: number;
  created_by?: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  tags?: string[];
}

export interface DownloadableDocument {
  id: number;
  title: string;
  description?: string;
  ai_guidance?: string;
  category: string;
  file: string;
  file_url?: string;
  file_name: string;
  file_size: number;
  file_type: string;
  is_active: boolean;
  download_count: number;
  share_count: number;
  requires_approval?: boolean;
  expiry_date?: string;
  created_by?: number;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  tags?: string[];
}

export interface ResourceCategory {
  id: number;
  name: string;
  description?: string;
  color_code?: string;
  icon?: string;
  order: number;
  is_active: boolean;
}

export interface LinkStats {
  total_links: number;
  active_links: number;
  total_sends: number;
  top_categories: Array<{
    category: string;
    count: number;
    total_sends: number;
  }>;
  recent_activity: Array<{
    action: string;
    count: number;
  }>;
}

export interface DocumentStats {
  total_documents: number;
  active_documents: number;
  total_downloads: number;
  total_shares: number;
  top_categories: Array<{
    category: string;
    count: number;
    total_downloads: number;
    total_shares: number;
  }>;
  recent_activity: Array<{
    action: string;
    count: number;
  }>;
}

// API Base URL
const BASE_URL = '/knowledge-resources';

// Useful Links API
export const usefulLinksApi = {
  // List all useful links
  list: async (params?: {
    category?: string;
    active?: boolean;
  }): Promise<UsefulLink[]> => {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.append('category', params.category);
    if (params?.active !== undefined) searchParams.append('active', params.active.toString());
    
    const queryString = searchParams.toString();
    const url = `${BASE_URL}/useful-links/${queryString ? `?${queryString}` : ''}`;
    
    const response = await api.get(url);
    // Verificar se a resposta tem paginação (DRF)
    if (response.data && response.data.results) {
      return response.data.results;
    }
    // Se for array direto, retornar como está
    return Array.isArray(response.data) ? response.data : [];
  },

  // Get single useful link
  get: async (id: number): Promise<UsefulLink> => {
    const response = await api.get(`${BASE_URL}/useful-links/${id}/`);
    return response.data;
  },

  // Create new useful link
  create: async (data: Partial<UsefulLink>): Promise<UsefulLink> => {
    const response = await api.post(`${BASE_URL}/useful-links/`, data);
    return response.data;
  },

  // Update useful link
  update: async (id: number, data: Partial<UsefulLink>): Promise<UsefulLink> => {
    const response = await api.patch(`${BASE_URL}/useful-links/${id}/`, data);
    return response.data;
  },

  // Delete useful link
  delete: async (id: number): Promise<void> => {
    await api.delete(`${BASE_URL}/useful-links/${id}/`);
  },

  // Increment send count (when AI sends the link)
  incrementSendCount: async (id: number, context?: {
    context?: string;
    chat_session_id?: number;
  }): Promise<{ success: boolean; send_count: number }> => {
    const response = await api.post(`${BASE_URL}/useful-links/${id}/increment_send_count/`, context);
    return response.data;
  },

  // Get statistics
  getStats: async (): Promise<LinkStats> => {
    const response = await api.get(`${BASE_URL}/useful-links/stats/`);
    return response.data;
  },
};

// Downloadable Documents API
export const downloadableDocumentsApi = {
  // List all downloadable documents
  list: async (params?: {
    category?: string;
    active?: boolean;
    file_type?: string;
  }): Promise<DownloadableDocument[]> => {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.append('category', params.category);
    if (params?.active !== undefined) searchParams.append('active', params.active.toString());
    if (params?.file_type) searchParams.append('file_type', params.file_type);
    
    const queryString = searchParams.toString();
    const url = `${BASE_URL}/downloadable-documents/${queryString ? `?${queryString}` : ''}`;
    
    const response = await api.get(url);
    // Verificar se a resposta tem paginação (DRF)
    if (response.data && response.data.results) {
      return response.data.results;
    }
    // Se for array direto, retornar como está
    return Array.isArray(response.data) ? response.data : [];
  },

  // Get single downloadable document
  get: async (id: number): Promise<DownloadableDocument> => {
    const response = await api.get(`${BASE_URL}/downloadable-documents/${id}/`);
    return response.data;
  },

  // Create new downloadable document
  create: async (data: FormData): Promise<DownloadableDocument> => {
    const response = await api.post(`${BASE_URL}/downloadable-documents/`, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Update downloadable document
  update: async (id: number, data: FormData | Partial<DownloadableDocument>): Promise<DownloadableDocument> => {
    const headers = data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {};
    const response = await api.patch(`${BASE_URL}/downloadable-documents/${id}/`, data, { headers });
    return response.data;
  },

  // Delete downloadable document
  delete: async (id: number): Promise<void> => {
    await api.delete(`${BASE_URL}/downloadable-documents/${id}/`);
  },

  // Increment download count
  incrementDownloadCount: async (id: number, context?: {
    context?: string;
    chat_session_id?: number;
  }): Promise<{ success: boolean; download_count: number }> => {
    const response = await api.post(`${BASE_URL}/downloadable-documents/${id}/increment_download_count/`, context);
    return response.data;
  },

  // Increment share count (when AI shares the document)
  incrementShareCount: async (id: number, context?: {
    context?: string;
    chat_session_id?: number;
  }): Promise<{ success: boolean; share_count: number }> => {
    const response = await api.post(`${BASE_URL}/downloadable-documents/${id}/increment_share_count/`, context);
    return response.data;
  },

  // Get statistics
  getStats: async (): Promise<DocumentStats> => {
    const response = await api.get(`${BASE_URL}/downloadable-documents/stats/`);
    return response.data;
  },
};

// Resource Categories API
export const categoriesApi = {
  // List all categories
  list: async (): Promise<ResourceCategory[]> => {
    const response = await api.get(`${BASE_URL}/categories/`);
    return response.data;
  },

  // Get single category
  get: async (id: number): Promise<ResourceCategory> => {
    const response = await api.get(`${BASE_URL}/categories/${id}/`);
    return response.data;
  },

  // Create new category
  create: async (data: Partial<ResourceCategory>): Promise<ResourceCategory> => {
    const response = await api.post(`${BASE_URL}/categories/`, data);
    return response.data;
  },

  // Update category
  update: async (id: number, data: Partial<ResourceCategory>): Promise<ResourceCategory> => {
    const response = await api.patch(`${BASE_URL}/categories/${id}/`, data);
    return response.data;
  },

  // Delete category
  delete: async (id: number): Promise<void> => {
    await api.delete(`${BASE_URL}/categories/${id}/`);
  },
};

// Combined API exports
export const knowledgeResourcesApi = {
  usefulLinks: usefulLinksApi,
  downloadableDocuments: downloadableDocumentsApi,
  categories: categoriesApi,
};