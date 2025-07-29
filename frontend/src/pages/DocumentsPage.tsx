import React, { useState } from 'react';
import { MainLayout } from '../components/MainLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  FileText,
  Upload,
  Trash2,
  Eye,
  Download,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  TrendingUp,
  FileIcon,
  Search,
} from 'lucide-react';
import { documentsApi } from '../services/documentsApi';

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

export const DocumentsPage: React.FC = () => {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentTitle, setDocumentTitle] = useState('');
  const [isDownloadable, setIsDownloadable] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [documentContent, setDocumentContent] = useState('');

  const queryClient = useQueryClient();

  // Queries
  const { data: stats } = useQuery<DocumentStats>({
    queryKey: ['documentStats'],
    queryFn: documentsApi.getStats,
    refetchInterval: (query) => {
      // Só atualizar automaticamente se houver documentos processando
      const statsData = query.state.data;
      if (statsData && typeof statsData === 'object' && (statsData.processing_documents > 0 || statsData.pending_documents > 0)) {
        return 5000; // 5 segundos se há processamento em andamento
      }
      return false; // Não atualizar automaticamente se não há processamento
    },
  });

  const { data: documents, isLoading, error } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
    refetchInterval: (query) => {
      // Só atualizar automaticamente se houver documentos processando
      const documentsData = query.state.data;
      if (Array.isArray(documentsData) && documentsData.some((doc: Document) => doc.status === 'processing' || doc.status === 'pending')) {
        return 5000; // 5 segundos se há documentos processando
      }
      return false; // Não atualizar automaticamente se todos estão processados
    },
  });

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: documentsApi.upload,
    onSuccess: () => {
      toast.success('Documento enviado para processamento');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documentStats'] });
      setUploadDialogOpen(false);
      resetUploadForm();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Erro ao enviar documento');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      toast.success('Documento excluído com sucesso');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documentStats'] });
      setDeleteDialogOpen(false);
    },
    onError: () => {
      toast.error('Erro ao excluir documento');
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: documentsApi.reprocess,
    onSuccess: () => {
      toast.success('Documento enviado para reprocessamento');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: () => {
      toast.error('Erro ao reprocessar documento');
    },
  });

  // Helpers
  const resetUploadForm = () => {
    setSelectedFile(null);
    setDocumentTitle('');
    setIsDownloadable(false);
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-500" />;
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'processed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      pending: 'bg-gray-100 text-gray-800',
      processing: 'bg-blue-100 text-blue-800',
      processed: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
    };

    const statusLabels = {
      pending: 'Pendente',
      processing: 'Processando',
      processed: 'Processado',
      error: 'Erro',
    };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClasses[status as keyof typeof statusClasses]}`}>
        {getStatusIcon(status)}
        <span className="ml-1">{statusLabels[status as keyof typeof statusLabels]}</span>
      </span>
    );
  };

  const getRankingBadge = (accessCount: number, allDocuments: Document[]) => {
    if (!allDocuments || allDocuments.length === 0) return null;

    const sortedByAccess = [...allDocuments].sort((a, b) => b.access_count - a.access_count);
    const position = sortedByAccess.findIndex(doc => doc.access_count === accessCount) + 1;

    if (position === 1 && accessCount > 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <TrendingUp className="h-3 w-3 mr-1" />
          Mais acessado
        </span>
      );
    } else if (position <= 3 && accessCount > 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          <TrendingUp className="h-3 w-3 mr-1" />
          Top {position}
        </span>
      );
    } else if (position <= 10 && accessCount > 0) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          Top 10
        </span>
      );
    }
    return null;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!documentTitle) {
        setDocumentTitle(file.name);
      }
    }
  };

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error('Selecione um arquivo');
      return;
    }

    uploadMutation.mutate({
      file: selectedFile,
      title: documentTitle || selectedFile.name,
      is_downloadable: isDownloadable,
    });
  };

  const handleViewContent = async (doc: Document) => {
    try {
      const content = await documentsApi.getContent(doc.id);
      setDocumentContent(content.content);
      setSelectedDocument(doc);
      setViewDialogOpen(true);
    } catch (error) {
      toast.error('Erro ao carregar conteúdo do documento');
    }
  };

  const filteredDocuments = Array.isArray(documents) ? documents.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  ) : [];

  return (
    <MainLayout>
      <div className="h-full overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Gestão de Documentos
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Área administrativa para upload e gerenciamento de documentos
            </p>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {stats.total_documents}
                    </p>
                  </div>
                  <FileText className="h-8 w-8 text-gray-400" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Processados</p>
                    <p className="text-2xl font-semibold text-green-600 dark:text-green-500">
                      {stats.processed_documents}
                    </p>
                  </div>
                  <CheckCircle className="h-8 w-8 text-green-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Em Processamento</p>
                    <p className="text-2xl font-semibold text-blue-600 dark:text-blue-500">
                      {stats.processing_documents + stats.pending_documents}
                    </p>
                  </div>
                  <RefreshCw className="h-8 w-8 text-blue-500" />
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Chunks</p>
                    <p className="text-2xl font-semibold text-purple-600 dark:text-purple-500">
                      {stats.total_chunks}
                    </p>
                  </div>
                  <FileIcon className="h-8 w-8 text-purple-500" />
                </div>
              </div>
            </div>
          )}

          {/* Toolbar */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar documentos..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-knight-primary focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['documents'] });
                  queryClient.invalidateQueries({ queryKey: ['documentStats'] });
                }}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
                title="Atualizar lista"
              >
                <RefreshCw className="h-4 w-4" />
                Atualizar
              </button>
              <button
                onClick={() => setUploadDialogOpen(true)}
                className="px-4 py-2 bg-knight-primary text-white rounded-lg hover:bg-knight-primary-dark transition-colors flex items-center gap-2"
              >
                <Upload className="h-4 w-4" />
                Upload Documento
              </button>
            </div>
          </div>

          {/* Documents Table */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            {error ? (
              <div className="p-8 text-center">
                <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                <p className="text-red-500 dark:text-red-400 mb-2">Erro ao carregar documentos</p>
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  Verifique se você está autenticado e tem permissões de administrador
                </p>
              </div>
            ) : isLoading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-knight-primary mx-auto"></div>
              </div>
            ) : filteredDocuments && filteredDocuments.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Documento
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Tipo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Ranking
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Data Upload
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {doc.title}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {formatFileSize(doc.file_size)}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-900 dark:text-white">
                            {doc.file_type.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {getStatusBadge(doc.status)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {getRankingBadge(doc.access_count, documents || [])}
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              {doc.access_count} acessos
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatDate(doc.uploaded_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex items-center gap-2">
                            {doc.status === 'processed' && (
                              <button
                                onClick={() => handleViewContent(doc)}
                                className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                                title="Ver conteúdo"
                              >
                                <Eye className="h-4 w-4" />
                              </button>
                            )}
                            {doc.is_downloadable && (
                              <a
                                href={`${process.env.REACT_APP_API_URL}/api/documents/${doc.id}/download/`}
                                className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300"
                                title="Download"
                              >
                                <Download className="h-4 w-4" />
                              </a>
                            )}
                            {(doc.status === 'error' || doc.status === 'processed') && (
                              <button
                                onClick={() => reprocessMutation.mutate(doc.id)}
                                className="text-orange-600 hover:text-orange-900 dark:text-orange-400 dark:hover:text-orange-300"
                                title="Reprocessar"
                              >
                                <RefreshCw className="h-4 w-4" />
                              </button>
                            )}
                            <button
                              onClick={() => {
                                setSelectedDocument(doc);
                                setDeleteDialogOpen(true);
                              }}
                              className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                              title="Excluir"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">Nenhum documento encontrado</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Upload Dialog */}
      {uploadDialogOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Upload de Documento
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Arquivo
                </label>
                <input
                  type="file"
                  onChange={handleFileSelect}
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-knight-primary focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  PDF, Word, Excel, PowerPoint, TXT ou Markdown (máx. 50MB)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Título do Documento
                </label>
                <input
                  type="text"
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                  placeholder="Digite o título do documento"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-knight-primary focus:border-transparent dark:bg-gray-700 dark:text-white"
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="downloadable"
                  checked={isDownloadable}
                  onChange={(e) => setIsDownloadable(e.target.checked)}
                  className="h-4 w-4 text-knight-primary focus:ring-knight-primary border-gray-300 rounded"
                />
                <label htmlFor="downloadable" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  Disponível para download
                </label>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setUploadDialogOpen(false);
                  resetUploadForm();
                }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleUpload}
                disabled={!selectedFile || uploadMutation.isPending}
                className="px-4 py-2 bg-knight-primary text-white rounded-lg hover:bg-knight-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploadMutation.isPending ? 'Enviando...' : 'Enviar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Content Dialog */}
      {viewDialogOpen && selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full h-[80vh] flex flex-col">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {selectedDocument.title}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Conteúdo em Markdown
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-mono">
                {documentContent}
              </pre>
            </div>

            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                onClick={() => {
                  setViewDialogOpen(false);
                  setDocumentContent('');
                  setSelectedDocument(null);
                }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteDialogOpen && selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Confirmar Exclusão
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Tem certeza que deseja excluir o documento "{selectedDocument.title}"? Esta ação não pode ser desfeita.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setDeleteDialogOpen(false);
                  setSelectedDocument(null);
                }}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  if (selectedDocument) {
                    deleteMutation.mutate(selectedDocument.id);
                  }
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleteMutation.isPending ? 'Excluindo...' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
};