import React, { useState, useCallback } from 'react';
import { MainLayout } from '../components/MainLayout';
import { 
  Upload, 
  FileText, 
  Trash2, 
  Download, 
  Search, 
  Plus,
  CheckCircle,
  AlertCircle,
  Clock,
  RotateCcw,
  Eye,
  TestTube,
  X
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import toast from 'react-hot-toast';

interface Document {
  id: number;
  title: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'processed' | 'error';
  is_downloadable: boolean;
  uploaded_at: string;
  processed_at?: string;
  processing_error?: string;
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

export const DocumentsPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [isDownloadable, setIsDownloadable] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  // Fetch documents
  const { data: documents = [], isLoading: documentsLoading, error: documentsError } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: async () => {
      const response = await api.get('/documents/');
      return Array.isArray(response.data) ? response.data : [];
    }
  });

  // Handle documents error
  React.useEffect(() => {
    if (documentsError) {
      console.error('Erro ao carregar documentos:', documentsError);
      toast.error('Erro ao carregar documentos');
    }
  }, [documentsError]);

  // Fetch document stats
  const { data: stats } = useQuery<DocumentStats>({
    queryKey: ['document-stats'],
    queryFn: async () => {
      const response = await api.get('/documents/stats/');
      return response.data;
    }
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const response = await api.post('/documents/upload/', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success('Documento enviado com sucesso!');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-stats'] });
      setSelectedFiles(null);
      setUploadTitle('');
      setIsDownloadable(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Erro ao enviar documento');
    }
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (documentId: number) => {
      await api.delete(`/documents/${documentId}/`);
    },
    onSuccess: () => {
      toast.success('Documento removido com sucesso!');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-stats'] });
    },
    onError: () => {
      toast.error('Erro ao remover documento');
    }
  });

  // Reprocess mutation
  const reprocessMutation = useMutation({
    mutationFn: async (documentId: number) => {
      await api.post(`/documents/${documentId}/reprocess/`);
    },
    onSuccess: () => {
      toast.success('Reprocessamento iniciado!');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-stats'] });
    },
    onError: () => {
      toast.error('Erro ao reprocessar documento');
    }
  });

  // Test Agno search mutation
  const testAgnoMutation = useMutation({
    mutationFn: async (query: string) => {
      const response = await api.post('/documents/test-agno-search/', { 
        query, 
        limit: 5 
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Busca realizada! ${data.results_count} resultados encontrados`);
    },
    onError: () => {
      toast.error('Erro ao testar busca no Agno');
    }
  });

  // View document content
  const { data: documentContent, refetch: refetchContent } = useQuery({
    queryKey: ['document-content', selectedDocumentId],
    queryFn: async () => {
      if (!selectedDocumentId) return null;
      const response = await api.get(`/documents/${selectedDocumentId}/content/`);
      return response.data;
    },
    enabled: false
  });

  // Test specific document in Agno
  const { data: agnoTestData, refetch: refetchAgnoTest } = useQuery({
    queryKey: ['agno-test', selectedDocumentId],
    queryFn: async () => {
      if (!selectedDocumentId) return null;
      const response = await api.get(`/documents/${selectedDocumentId}/agno_test/`);
      return response.data;
    },
    enabled: false
  });

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    setSelectedFiles(files);
    if (files && files.length > 0 && !uploadTitle) {
      const fileName = files[0].name;
      const nameWithoutExt = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
      setUploadTitle(nameWithoutExt);
    }
  }, [uploadTitle]);

  const handleUpload = useCallback(() => {
    if (!selectedFiles || selectedFiles.length === 0) {
      toast.error('Selecione um arquivo para enviar');
      return;
    }

    if (!uploadTitle.trim()) {
      toast.error('Digite um título para o documento');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFiles[0]);
    formData.append('title', uploadTitle.trim());
    formData.append('is_downloadable', isDownloadable ? 'true' : 'false');

    uploadMutation.mutate(formData);
  }, [selectedFiles, uploadTitle, isDownloadable, uploadMutation]);

  const handleDownload = useCallback(async (doc: Document) => {
    try {
      const response = await api.get(`/documents/${doc.id}/download/`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = window.document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.original_filename);
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Download iniciado!');
    } catch (error) {
      toast.error('Erro ao baixar documento');
    }
  }, []);

  const handleTestAgnoSearch = useCallback(() => {
    if (!testQuery.trim()) {
      toast.error('Digite uma consulta para testar');
      return;
    }
    testAgnoMutation.mutate(testQuery);
  }, [testQuery, testAgnoMutation]);

  const handleViewDocument = useCallback((documentId: number) => {
    setSelectedDocumentId(documentId);
    refetchContent();
    refetchAgnoTest();
  }, [refetchContent, refetchAgnoTest]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'processing':
        return <Clock className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'processed': return 'Processado';
      case 'processing': return 'Processando';
      case 'error': return 'Erro';
      case 'pending': return 'Pendente';
      default: return status;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const filteredDocuments = Array.isArray(documents) ? documents.filter((doc: Document) =>
    doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase())
  ) : [];

  return (
    <MainLayout>
      <div className="h-full overflow-y-auto">
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Documentos
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Gerencie a base de conhecimento do Knight Agent
            </p>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {stats.total_documents}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Total</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {stats.processed_documents}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Processados</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {stats.processing_documents + stats.pending_documents}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Pendentes</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {stats.error_documents}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">Erros</div>
              </div>
            </div>
          )}

          {/* Upload Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
              <Plus className="h-5 w-5 mr-2" />
              Adicionar Documento
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Título do Documento
                </label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="Digite o título do documento"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Arquivo
                </label>
                <input
                  type="file"
                  onChange={handleFileSelect}
                  accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                />
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Formatos suportados: PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, TXT, MD (máx. 50MB)
                </p>
              </div>

              <div className="flex items-center">
                <input
                  id="downloadable"
                  type="checkbox"
                  checked={isDownloadable}
                  onChange={(e) => setIsDownloadable(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="downloadable" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Permitir download pelos usuários
                </label>
              </div>

              <button
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Upload className="h-4 w-4 mr-2" />
                {uploadMutation.isPending ? 'Enviando...' : 'Enviar Documento'}
              </button>
            </div>
          </div>

          {/* Agno Testing Section */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
              <TestTube className="h-5 w-5 mr-2" />
              Teste de Integração Agno
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Testar Busca no Agno
                </label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    placeholder="Digite uma consulta para buscar nos documentos..."
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                  <button
                    onClick={handleTestAgnoSearch}
                    disabled={testAgnoMutation.isPending}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testAgnoMutation.isPending ? 'Testando...' : 'Testar'}
                  </button>
                </div>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Teste se o Agno consegue encontrar informações nos documentos processados
                </p>
              </div>

              {/* Results */}
              {testAgnoMutation.data && (
                <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    Resultados da Busca: "{testAgnoMutation.data.query}"
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                      <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                        {testAgnoMutation.data.results_count}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Resultados</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-green-600 dark:text-green-400">
                        {testAgnoMutation.data.total_processed_docs}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Docs Processados</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-purple-600 dark:text-purple-400">
                        {testAgnoMutation.data.agno_working === true ? '✓' : '✗'}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Agno Ativo</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-orange-600 dark:text-orange-400">
                        {Math.round((testAgnoMutation.data.results_count / Math.max(testAgnoMutation.data.total_processed_docs, 1)) * 100)}%
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">Taxa de Acerto</div>
                    </div>
                  </div>
                  
                  {testAgnoMutation.data.search_results.length > 0 && (
                    <div>
                      <h5 className="font-medium text-gray-900 dark:text-white mb-2">Documentos Encontrados:</h5>
                      <div className="space-y-2">
                        {testAgnoMutation.data.search_results.map((result: any, index: number) => (
                          <div key={index} className="p-2 bg-white dark:bg-gray-800 rounded border">
                            <div className="flex justify-between items-start">
                              <div>
                                <div className="font-medium text-sm">
                                  Doc ID: {result.document_id || 'N/A'}
                                </div>
                                <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                  Score: {result.score?.toFixed(3) || 'N/A'}
                                </div>
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {result.content?.substring(0, 100)}...
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Search and Documents List */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Buscar documentos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              {documentsLoading ? (
                <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                  Carregando documentos...
                </div>
              ) : filteredDocuments.length === 0 ? (
                <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                  {Array.isArray(documents) && documents.length === 0 ? 'Nenhum documento encontrado' : 'Nenhum documento corresponde à busca'}
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Documento
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Tamanho
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Data
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {filteredDocuments.map((document: Document) => (
                      <tr key={document.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <FileText className="h-8 w-8 text-gray-400 mr-3" />
                            <div>
                              <div className="text-sm font-medium text-gray-900 dark:text-white">
                                {document.title}
                              </div>
                              <div className="text-sm text-gray-500 dark:text-gray-400">
                                {document.original_filename}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getStatusIcon(document.status)}
                            <span className="ml-2 text-sm text-gray-900 dark:text-white">
                              {getStatusText(document.status)}
                            </span>
                          </div>
                          {document.status === 'error' && document.processing_error && (
                            <div className="text-xs text-red-500 mt-1">
                              {document.processing_error}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                          {formatFileSize(document.file_size)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                          {new Date(document.uploaded_at).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex items-center justify-end space-x-2">
                            {document.status === 'processed' && (
                              <button
                                onClick={() => handleViewDocument(document.id)}
                                className="text-purple-600 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300"
                                title="Ver conteúdo e teste Agno"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                            )}
                            {document.status === 'error' && (
                              <button
                                onClick={() => reprocessMutation.mutate(document.id)}
                                disabled={reprocessMutation.isPending}
                                className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                                title="Reprocessar"
                              >
                                <RotateCcw className="h-4 w-4" />
                              </button>
                            )}
                            {document.is_downloadable && (
                              <button
                                onClick={() => handleDownload(document)}
                                className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300"
                                title="Download"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                            )}
                            <button
                              onClick={() => deleteMutation.mutate(document.id)}
                              disabled={deleteMutation.isPending}
                              className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                              title="Remover"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </main>

        {/* Document Content Modal */}
        {selectedDocumentId && (documentContent || agnoTestData) && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
              <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={() => setSelectedDocumentId(null)} />
              
              <div className="inline-block w-full max-w-4xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white dark:bg-gray-800 shadow-xl rounded-lg">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Documento #{selectedDocumentId}
                  </h3>
                  <button
                    onClick={() => setSelectedDocumentId(null)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="space-y-6">
                  {/* Document Content */}
                  {documentContent && (
                    <div>
                      <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        Conteúdo Markdown
                      </h4>
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 max-h-60 overflow-y-auto">
                        <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                          {documentContent.content || 'Nenhum conteúdo disponível'}
                        </pre>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-medium">Chunks: </span>
                          {documentContent.chunks_count || 0}
                        </div>
                        <div>
                          <span className="font-medium">Título: </span>
                          {documentContent.title || 'N/A'}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Agno Test Results */}
                  {agnoTestData && (
                    <div>
                      <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        Teste de Integração Agno
                      </h4>
                      
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                          <div className="text-center">
                            <div className={`text-xl font-bold ${agnoTestData.indexed_in_agno ? 'text-green-600' : 'text-red-600'}`}>
                              {agnoTestData.indexed_in_agno ? '✓' : '✗'}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">Indexado no Agno</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                              {agnoTestData.agno_search_results?.length || 0}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">Resultados por Título</div>
                          </div>
                          <div className="text-center">
                            <div className={`text-xl font-bold ${agnoTestData.agno_document_by_id ? 'text-green-600' : 'text-orange-600'}`}>
                              {agnoTestData.agno_document_by_id ? '✓' : '✗'}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">Busca por ID</div>
                          </div>
                        </div>

                        {agnoTestData.markdown_preview && (
                          <div>
                            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Preview do Markdown:</h5>
                            <div className="bg-white dark:bg-gray-800 rounded p-3 text-sm text-gray-700 dark:text-gray-300">
                              <pre className="whitespace-pre-wrap">{agnoTestData.markdown_preview}</pre>
                            </div>
                          </div>
                        )}

                        {agnoTestData.agno_search_results && agnoTestData.agno_search_results.length > 0 && (
                          <div className="mt-4">
                            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Resultados da Busca no Agno:</h5>
                            <div className="space-y-2 max-h-40 overflow-y-auto">
                              {agnoTestData.agno_search_results.map((result: any, index: number) => (
                                <div key={index} className="p-2 bg-white dark:bg-gray-800 rounded border text-sm">
                                  <div className="font-medium">Score: {result.score?.toFixed(3) || 'N/A'}</div>
                                  <div className="text-gray-600 dark:text-gray-400 mt-1">
                                    {result.content?.substring(0, 150)}...
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {agnoTestData.error && (
                          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
                            <h5 className="font-medium text-red-800 dark:text-red-400 mb-1">Erro:</h5>
                            <p className="text-sm text-red-700 dark:text-red-300">{agnoTestData.error}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={() => setSelectedDocumentId(null)}
                    className="px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-400 dark:hover:bg-gray-500"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};