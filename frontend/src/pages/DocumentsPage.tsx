import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  Link as LinkIcon,
  Plus,
  Activity,
  Edit2,
  Copy,
  ExternalLink,
} from 'lucide-react';
import { documentsApi } from '../services/documentsApi';
import { knowledgeResourcesApi, UsefulLink, DownloadableDocument, ResourceCategory, categoriesApi } from '../services/knowledgeResourcesApi';
import { DataTable } from '../components/DataTable';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { PopularityRankingBadge } from '../components/PopularityRankingBadge';

// Tipos
interface Document {
  id: number;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'processed' | 'error';
  error_message?: string;
  created_at: string;
  updated_at: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  page_count?: number;
  chunk_count?: number;
  document_metadata?: any;
  tags: string[];
  access_count: number;
  uploaded_by_name?: string;
  uploaded_by_email?: string;
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

// UsefulLink e DownloadableDocument agora vêm do knowledgeResourcesApi

export const DocumentsPage: React.FC = () => {
  const { t } = useTranslation();

  // States para documentos (existente)
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentTitle, setDocumentTitle] = useState('');
  const [documentContent, setDocumentContent] = useState('');
  const [activeTab, setActiveTab] = useState('knowledge-base');

  // States para Links Úteis
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [editingLink, setEditingLink] = useState<UsefulLink | null>(null);
  const [linkTitle, setLinkTitle] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [linkDescription, setLinkDescription] = useState('');
  const [linkAiGuidance, setLinkAiGuidance] = useState('');
  const [linkCategory, setLinkCategory] = useState('');

  // States para Documentos Baixáveis
  const [downloadableDocDialogOpen, setDownloadableDocDialogOpen] = useState(false);
  const [editingDownloadableDoc, setEditingDownloadableDoc] = useState<DownloadableDocument | null>(null);
  const [downloadableDocTitle, setDownloadableDocTitle] = useState('');
  const [downloadableDocDescription, setDownloadableDocDescription] = useState('');
  const [downloadableDocAiGuidance, setDownloadableDocAiGuidance] = useState('');
  const [downloadableDocCategory, setDownloadableDocCategory] = useState('');
  const [downloadableDocFile, setDownloadableDocFile] = useState<File | null>(null);

  // State for new category creation
  const [newCategoryName, setNewCategoryName] = useState('');
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);

  // Configuração dinâmica dos títulos baseado na aba ativa
  const getTabConfig = () => {
    switch (activeTab) {
      case 'knowledge-base':
        return {
          title: t('documentsPage.knowledge_base'),
          subtitle: t('documentsPage.knowledge_base_desc')
        };
      case 'useful-links':
        return {
          title: t('documentsPage.useful_links'),
          subtitle: t('documentsPage.useful_links_desc')
        };
      case 'downloadable-docs':
        return {
          title: t('documentsPage.forms_and_docs'),
          subtitle: t('documentsPage.forms_and_docs_desc')
        };
      default:
        return {
          title: t('documentsPage.knowledge_management'),
          subtitle: t('documentsPage.admin_area_desc')
        };
    }
  };

  const tabConfig = getTabConfig();

  const queryClient = useQueryClient();

  // Queries
  const { data: stats } = useQuery<DocumentStats>({
    queryKey: ['documentStats'],
    queryFn: documentsApi.getStats,
    refetchInterval: (query) => {
      const statsData = query.state.data;
      if (statsData && typeof statsData === 'object' && (statsData.processing_documents > 0 || statsData.pending_documents > 0)) {
        return 5000;
      }
      return false;
    },
  });

  const { data: documents, isLoading, error } = useQuery<Document[]>({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
    refetchInterval: (query) => {
      const documentsData = query.state.data;
      if (Array.isArray(documentsData) && documentsData.some((doc: Document) => doc.status === 'processing' || doc.status === 'pending')) {
        return 5000; // Refresh rápido para documentos processando
      }
      return 30000; // Refresh a cada 30s para capturar mudanças no access_count
    },
  });

  // APIs reais para links úteis e documentos baixáveis
  const { data: usefulLinks, isLoading: linksLoading, error: linksError } = useQuery<UsefulLink[]>({
    queryKey: ['usefulLinks'],
    queryFn: () => knowledgeResourcesApi.usefulLinks.list({ active: true }),
  });

  const { data: downloadableDocuments, isLoading: docsLoading, error: docsError } = useQuery<DownloadableDocument[]>({
    queryKey: ['downloadableDocuments'],
    queryFn: () => knowledgeResourcesApi.downloadableDocuments.list({ active: true }),
  });

  // Query for categories
  const { data: categories = [], isLoading: categoriesLoading } = useQuery<ResourceCategory[]>({
    queryKey: ['resourceCategories'],
    queryFn: () => categoriesApi.list(true),
  });

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: documentsApi.upload,
    onSuccess: () => {
      toast.success(t('documentsPage.document_sent_processing'));
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documentStats'] });
      setUploadDialogOpen(false);
      resetUploadForm();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || t('documentsPage.error_sending_document'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: documentsApi.delete,
    onSuccess: () => {
      toast.success(t('documentsPage.document_deleted_success'));
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['documentStats'] });
      setDeleteDialogOpen(false);
    },
    onError: () => {
      toast.error(t('documentsPage.error_deleting_document'));
    },
  });

  // Mutations para Links Úteis
  const createLinkMutation = useMutation({
    mutationFn: knowledgeResourcesApi.usefulLinks.create,
    onSuccess: () => {
      toast.success(t('documentsPage.link_created_success'));
      queryClient.invalidateQueries({ queryKey: ['usefulLinks'] });
      setLinkDialogOpen(false);
      resetLinkForm();
    },
    onError: () => {
      toast.error(t('documentsPage.error_creating_link'));
    },
  });

  const updateLinkMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<UsefulLink> }) =>
      knowledgeResourcesApi.usefulLinks.update(id, data),
    onSuccess: () => {
      toast.success(t('documentsPage.link_updated_success'));
      queryClient.invalidateQueries({ queryKey: ['usefulLinks'] });
      setLinkDialogOpen(false);
      resetLinkForm();
    },
    onError: () => {
      toast.error(t('documentsPage.error_updating_link'));
    },
  });

  const deleteLinkMutation = useMutation({
    mutationFn: knowledgeResourcesApi.usefulLinks.delete,
    onSuccess: () => {
      toast.success(t('documentsPage.link_deleted_success'));
      queryClient.invalidateQueries({ queryKey: ['usefulLinks'] });
    },
    onError: () => {
      toast.error(t('documentsPage.error_deleting_link'));
    },
  });

  // Mutations para Documentos Baixáveis
  const createDownloadableDocMutation = useMutation({
    mutationFn: knowledgeResourcesApi.downloadableDocuments.create,
    onSuccess: () => {
      toast.success(t('documentsPage.document_created_success'));
      queryClient.invalidateQueries({ queryKey: ['downloadableDocuments'] });
      setDownloadableDocDialogOpen(false);
      resetDownloadableDocForm();
    },
    onError: () => {
      toast.error(t('documentsPage.error_creating_document'));
    },
  });

  const updateDownloadableDocMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: FormData | Partial<DownloadableDocument> }) =>
      knowledgeResourcesApi.downloadableDocuments.update(id, data),
    onSuccess: () => {
      toast.success(t('documentsPage.document_updated_success'));
      queryClient.invalidateQueries({ queryKey: ['downloadableDocuments'] });
      setDownloadableDocDialogOpen(false);
      resetDownloadableDocForm();
    },
    onError: () => {
      toast.error(t('documentsPage.error_updating_document'));
    },
  });

  const deleteDownloadableDocMutation = useMutation({
    mutationFn: knowledgeResourcesApi.downloadableDocuments.delete,
    onSuccess: () => {
      toast.success(t('documentsPage.document_deleted_success_modal'));
      queryClient.invalidateQueries({ queryKey: ['downloadableDocuments'] });
    },
    onError: () => {
      toast.error(t('documentsPage.error_deleting_document_modal'));
    },
  });


  // Helpers
  const resetUploadForm = () => {
    setSelectedFile(null);
    setDocumentTitle('');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) {
      return `${bytes} bytes`;
    } else if (bytes < 1024 * 1024) {
      const kb = bytes / 1024;
      return `${kb.toFixed(1)} KB`;
    } else {
      const mb = bytes / (1024 * 1024);
      return `${mb.toFixed(2)} MB`;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-foreground" />;
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-foreground animate-spin" />;
      case 'processed':
        return <CheckCircle className="h-4 w-4 text-foreground" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-foreground" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { variant: 'status-pending' as const, label: t('documentsPage.pending') },
      processing: { variant: 'status-processing' as const, label: t('documentsPage.processing_status') },
      processed: { variant: 'status-processed' as const, label: t('documentsPage.processed_status') },
      error: { variant: 'status-error' as const, label: t('documentsPage.error_status') },
    };

    const config = statusConfig[status as keyof typeof statusConfig];
    if (!config) return null;

    return (
      <div className="flex justify-start">
        <Badge variant={config.variant} className="flex items-center gap-1 whitespace-nowrap">
          {getStatusIcon(status)}
          {config.label}
        </Badge>
      </div>
    );
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
      toast.error(t('documentsPage.select_file'));
      return;
    }

    uploadMutation.mutate({
      file: selectedFile,
      title: documentTitle || selectedFile.name,
      is_downloadable: true,
    });
  };

  const handleViewContent = async (doc: Document) => {
    try {
      const content = await documentsApi.getContent(doc.id);
      setDocumentContent(content.content);
      setSelectedDocument(doc);
      setViewDialogOpen(true);
    } catch (error) {
      toast.error(t('chatPage.error_loading_content'));
    }
  };

  // Funções helper para Links Úteis
  const resetLinkForm = () => {
    setLinkTitle('');
    setLinkUrl('');
    setLinkDescription('');
    setLinkAiGuidance('');
    setLinkCategory('');
    setEditingLink(null);
  };

  const handleOpenLinkDialog = (link?: UsefulLink) => {
    if (link) {
      setEditingLink(link);
      setLinkTitle(link.title);
      setLinkUrl(link.url);
      setLinkDescription(link.description ?? '');
      setLinkAiGuidance(link.ai_guidance ?? '');
      setLinkCategory(link.category);
    } else {
      resetLinkForm();
    }
    setLinkDialogOpen(true);
  };

  const handleSaveLink = () => {
    if (!linkTitle || !linkUrl) {
      toast.error(t('documentsPage.title_and_url_required'));
      return;
    }

    const linkData = {
      title: linkTitle,
      url: linkUrl,
      description: linkDescription,
      ai_guidance: linkAiGuidance,
      category: linkCategory,
      is_active: true, // Garantir que o link seja criado como ativo
    };

    if (editingLink) {
      updateLinkMutation.mutate({ id: editingLink.id, data: linkData });
    } else {
      createLinkMutation.mutate(linkData);
    }
  };

  // Funções helper para Documentos Baixáveis
  const resetDownloadableDocForm = () => {
    setDownloadableDocTitle('');
    setDownloadableDocDescription('');
    setDownloadableDocAiGuidance('');
    setDownloadableDocCategory('');
    setDownloadableDocFile(null);
    setEditingDownloadableDoc(null);
  };

  const handleOpenDownloadableDocDialog = (doc?: DownloadableDocument) => {
    if (doc) {
      setEditingDownloadableDoc(doc);
      setDownloadableDocTitle(doc.title);
      setDownloadableDocDescription(doc.description ?? '');
      setDownloadableDocAiGuidance(doc.ai_guidance ?? '');
      setDownloadableDocCategory(doc.category);
    } else {
      resetDownloadableDocForm();
    }
    setDownloadableDocDialogOpen(true);
  };

  const handleSaveDownloadableDoc = () => {
    if (!downloadableDocTitle || (!downloadableDocFile && !editingDownloadableDoc)) {
      toast.error(t('documentsPage.title_and_file_required'));
      return;
    }

    const formData = new FormData();
    formData.append('title', downloadableDocTitle);
    formData.append('description', downloadableDocDescription);
    formData.append('ai_guidance', downloadableDocAiGuidance);
    formData.append('category', downloadableDocCategory);
    formData.append('is_active', 'true'); // Garantir que o documento seja criado como ativo
    
    if (downloadableDocFile) {
      formData.append('file', downloadableDocFile);
    }

    if (editingDownloadableDoc) {
      updateDownloadableDocMutation.mutate({ id: editingDownloadableDoc.id, data: formData });
    } else {
      createDownloadableDocMutation.mutate(formData);
    }
  };

  const handleDownloadableDocFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setDownloadableDocFile(file);
      if (!downloadableDocTitle) {
        setDownloadableDocTitle(file.name.replace(/\.[^/.]+$/, '')); // Remove extensão
      }
    }
  };

  // Colunas da tabela de documentos
  const documentColumns = [
    {
      accessorKey: 'title',
      header: t('documentsPage.document'),
      cell: ({ row }: { row: { original: Document } }) => {
        const doc = row.original;
        return (
          <div className="space-y-1">
            <div className="font-medium">{doc.title}</div>
            <div className="text-sm text-muted-foreground">
              {doc.file_type.toUpperCase()} • {formatFileSize(doc.file_size)}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'status',
      header: t('documentsPage.status'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => getStatusBadge(row.getValue('status')),
    },
    {
      accessorKey: 'uploaded_by_name',
      header: t('documentsPage.uploaded_by'),
      cell: ({ row }: { row: { original: Document } }) => {
        const name = row.original.uploaded_by_name;
        const email = row.original.uploaded_by_email;
        if (!name && !email) return <span className="text-muted-foreground">-</span>;
        return (
          <div className="text-sm">
            <div className="font-medium">{name || email?.split('@')[0]}</div>
            {email && <div className="text-xs text-muted-foreground">{email}</div>}
          </div>
        );
      },
    },
    {
      accessorKey: 'access_count',
      header: t('documentsPage.popularity'),
      cell: ({ row }: { row: { original: Document } }) => {
        const doc = row.original;
        return (
          <PopularityRankingBadge 
            document={doc}
            allDocuments={documents || []}
          />
        );
      },
    },
    {
      accessorKey: 'created_at',
      header: t('documentsPage.upload_date'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <span className="text-sm">{formatDate(row.getValue('created_at'))}</span>
      ),
    },
    {
      accessorKey: 'updated_at',
      header: t('documentsPage.last_updated'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <span className="text-sm">{formatDate(row.getValue('updated_at'))}</span>
      ),
    },
    {
      id: 'actions',
      header: t('documentsPage.actions'),
      cell: ({ row }: { row: { original: Document } }) => {
        const doc = row.original;
        return (
          <div className="flex items-center gap-2">
            {doc.status === 'processed' && (
              <button
                onClick={() => handleViewContent(doc)}
                title={t('documentsPage.view_content')}
                className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                style={{
                  backgroundColor: 'transparent'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#FFB833';
                  e.currentTarget.style.color = '#2A2A2A';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'inherit';
                }}
              >
                <Eye className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={async () => {
                try {
                  // Use direct window.open for file download with cookies
                  const downloadUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/documents/${doc.id}/download`;
                  const link = document.createElement('a');
                  link.href = downloadUrl;
                  link.download = doc.filename || `document-${doc.id}`;
                  link.target = '_blank';
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                } catch (error) {
                  toast.error(t('documentsPage.download_error'));
                }
              }}
              title={t('documentsPage.download')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              style={{
                backgroundColor: 'transparent'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#FFB833';
                e.currentTarget.style.color = '#2A2A2A';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'inherit';
              }}
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setSelectedDocument(doc);
                setDeleteDialogOpen(true);
              }}
              title={t('documentsPage.delete')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              style={{
                backgroundColor: 'transparent'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgb(239, 68, 68)';
                e.currentTarget.style.color = 'rgb(248, 250, 252)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = 'inherit';
              }}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        );
      },
    },
  ];

  // Colunas da tabela de Links Úteis
  const usefulLinksColumns = [
    {
      accessorKey: 'title',
      header: t('documentsPage.link'),
      className: 'w-[300px] max-w-[300px]',
      cell: ({ row }: { row: { original: UsefulLink } }) => {
        const link = row.original;
        const truncateUrl = (url: string, maxLength: number = 40) => {
          if (url.length <= maxLength) return url;

          // Try to show domain and some path
          const urlParts = url.split('://');
          if (urlParts.length > 1) {
            const afterProtocol = urlParts[1];
            if (afterProtocol.length > maxLength - 8) {
              return `${urlParts[0]}://${afterProtocol.substring(0, maxLength - 8)}...`;
            }
          }
          return url.substring(0, maxLength - 3) + '...';
        };

        return (
          <div className="space-y-1 max-w-xs">
            <div className="font-medium">{link.title}</div>
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <ExternalLink className="h-3 w-3 flex-shrink-0" />
              <span className="truncate" title={link.url}>
                {truncateUrl(link.url, 35)}
              </span>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'category',
      header: t('documentsPage.category'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <Badge variant="secondary" className="whitespace-nowrap">
          {row.getValue('category')}
        </Badge>
      ),
    },
    {
      accessorKey: 'send_count',
      header: t('documentsPage.sends'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue('send_count')}</span>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: t('documentsPage.created_at'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <span className="text-sm">{formatDate(row.getValue('created_at'))}</span>
      ),
    },
    {
      id: 'actions',
      header: t('documentsPage.actions'),
      cell: ({ row }: { row: { original: UsefulLink } }) => {
        const link = row.original;
        return (
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(link.url);
                toast.success(t('documentsPage.url_copied'));
              }}
              title={t('documentsPage.copy_url')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <Copy className="h-4 w-4" />
            </button>
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              title={t('documentsPage.open_link')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
            <button
              onClick={() => handleOpenLinkDialog(link)}
              title={t('documentsPage.edit')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <Edit2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                if (window.confirm(t('documentsPage.confirm_delete_link'))) {
                  deleteLinkMutation.mutate(link.id);
                }
              }}
              title={t('documentsPage.delete')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-destructive hover:text-destructive-foreground"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        );
      },
    },
  ];

  // Colunas da tabela de Documentos Baixáveis
  const downloadableDocumentsColumns = [
    {
      accessorKey: 'title',
      header: t('documentsPage.document'),
      cell: ({ row }: { row: { original: DownloadableDocument } }) => {
        const doc = row.original;
        return (
          <div className="space-y-1">
            <div className="font-medium">{doc.title}</div>
            <div className="text-sm text-muted-foreground">
              {doc.file_type.toUpperCase()} • {formatFileSize(doc.file_size)}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: 'category',
      header: 'Categoria',
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <Badge variant="secondary" className="whitespace-nowrap">
          {row.getValue('category')}
        </Badge>
      ),
    },
    {
      accessorKey: 'download_count',
      header: t('documentsPage.downloads_count'),
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <div className="flex items-center gap-2">
          <Download className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{row.getValue('download_count')}</span>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: 'Criado em',
      cell: ({ row }: { row: { getValue: (key: string) => any } }) => (
        <span className="text-sm">{formatDate(row.getValue('created_at'))}</span>
      ),
    },
    {
      id: 'actions',
      header: 'Ações',
      cell: ({ row }: { row: { original: DownloadableDocument } }) => {
        const doc = row.original;
        return (
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                // TODO: Implementar download do arquivo
                toast.success(t('documentsPage.download_started'));
              }}
              title={t('documentsPage.download_file')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <Download className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleOpenDownloadableDocDialog(doc)}
              title={t('documentsPage.edit')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <Edit2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                if (window.confirm(t('documentsPage.confirm_delete_document_modal'))) {
                  deleteDownloadableDocMutation.mutate(doc.id);
                }
              }}
              title={t('documentsPage.delete')}
              className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-destructive hover:text-destructive-foreground"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <MainLayout title={t('documents.title')} subtitle={t('documentsPage.knowledge_management')}>
      <div className="h-full overflow-y-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-4 sm:py-6 space-y-4 sm:space-y-6">
          
          {/* Header dinâmico baseado na aba ativa */}
          <div className="flex flex-col space-y-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground">{tabConfig.title}</h1>
            <p className="text-muted-foreground">
              {tabConfig.subtitle}
            </p>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              <Card className="p-4 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t('documentsPage.total_documents')}</p>
                    <p className="text-2xl font-bold text-muted-foreground">{stats.total_documents}</p>
                  </div>
                  <div className="relative -mt-5">
                    <FileText className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                      style={{
                        '--hover-color': 'rgb(var(--card-hover-icon))'
                      } as React.CSSProperties}
                      onMouseEnter={(e) => {
                        (e.target as HTMLElement).style.color = 'var(--hover-color)';
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLElement).style.color = '';
                      }}
                    />
                  </div>
                </div>
                
                {/* Shine Effect */}
                <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                  <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                       style={{
                         background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                       }}>
                  </div>
                </div>
                
                {/* Animated Background */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                     style={{
                       maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                       WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                     }}>
                  
                  {/* Animated Tiles */}
                  <div className="absolute inset-0">
                    <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.05)',
                      animation: 'randomPulse 3.2s ease-in-out infinite',
                      animationDelay: '0s'
                    }}></div>
                    <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.08)',
                      animation: 'randomPulse 2.8s ease-in-out infinite',
                      animationDelay: '0.9s'
                    }}></div>
                    <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.03)',
                      animation: 'randomPulse 3.5s ease-in-out infinite',
                      animationDelay: '1.8s'
                    }}></div>
                    <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.12)',
                      animation: 'randomPulse 2.3s ease-in-out infinite',
                      animationDelay: '2.1s'
                    }}></div>
                    <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.06)',
                      animation: 'randomPulse 4.1s ease-in-out infinite',
                      animationDelay: '0.4s'
                    }}></div>
                    <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.11)',
                      animation: 'randomPulse 2.7s ease-in-out infinite',
                      animationDelay: '1.3s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.04)',
                      animation: 'randomPulse 3.8s ease-in-out infinite',
                      animationDelay: '2.7s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.09)',
                      animation: 'randomPulse 3.1s ease-in-out infinite',
                      animationDelay: '1.6s'
                    }}></div>
                  </div>
                  
                  {/* Animated Lines */}
                  <div className="absolute inset-0">
                    <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                    <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t('documentsPage.processed')}</p>
                    <p className="text-2xl font-bold text-muted-foreground">{stats.processed_documents}</p>
                  </div>
                  <div className="relative -mt-5">
                    <CheckCircle className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                      style={{
                        '--hover-color': 'rgb(var(--card-hover-icon))'
                      } as React.CSSProperties}
                      onMouseEnter={(e) => {
                        (e.target as HTMLElement).style.color = 'var(--hover-color)';
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLElement).style.color = '';
                      }}
                    />
                  </div>
                </div>
                
                {/* Shine Effect */}
                <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                  <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                       style={{
                         background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                       }}>
                  </div>
                </div>
                
                {/* Animated Background */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                     style={{
                       maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                       WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                     }}>
                  
                  {/* Animated Tiles */}
                  <div className="absolute inset-0">
                    <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.04)',
                      animation: 'randomPulse 3.4s ease-in-out infinite',
                      animationDelay: '0.3s'
                    }}></div>
                    <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.09)',
                      animation: 'randomPulse 2.9s ease-in-out infinite',
                      animationDelay: '1.1s'
                    }}></div>
                    <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.07)',
                      animation: 'randomPulse 3.7s ease-in-out infinite',
                      animationDelay: '2.0s'
                    }}></div>
                    <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.11)',
                      animation: 'randomPulse 2.5s ease-in-out infinite',
                      animationDelay: '0.7s'
                    }}></div>
                    <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.05)',
                      animation: 'randomPulse 4.2s ease-in-out infinite',
                      animationDelay: '1.9s'
                    }}></div>
                    <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.08)',
                      animation: 'randomPulse 3.0s ease-in-out infinite',
                      animationDelay: '0.5s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.06)',
                      animation: 'randomPulse 3.6s ease-in-out infinite',
                      animationDelay: '1.4s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.10)',
                      animation: 'randomPulse 2.6s ease-in-out infinite',
                      animationDelay: '2.3s'
                    }}></div>
                  </div>
                  
                  {/* Animated Lines */}
                  <div className="absolute inset-0">
                    <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                    <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t('documentsPage.processing')}</p>
                    <p className="text-2xl font-bold text-muted-foreground">
                      {stats.processing_documents + stats.pending_documents}
                    </p>
                  </div>
                  <div className="relative -mt-5">
                    <RefreshCw className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                      style={{
                        '--hover-color': 'rgb(var(--card-hover-icon))'
                      } as React.CSSProperties}
                      onMouseEnter={(e) => {
                        (e.target as HTMLElement).style.color = 'var(--hover-color)';
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLElement).style.color = '';
                      }}
                    />
                  </div>
                </div>
                
                {/* Shine Effect */}
                <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                  <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                       style={{
                         background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                       }}>
                  </div>
                </div>
                
                {/* Animated Background */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                     style={{
                       maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                       WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                     }}>
                  
                  {/* Animated Tiles */}
                  <div className="absolute inset-0">
                    <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.08)',
                      animation: 'randomPulse 2.8s ease-in-out infinite',
                      animationDelay: '0.6s'
                    }}></div>
                    <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.04)',
                      animation: 'randomPulse 3.5s ease-in-out infinite',
                      animationDelay: '1.4s'
                    }}></div>
                    <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.10)',
                      animation: 'randomPulse 4.0s ease-in-out infinite',
                      animationDelay: '0.2s'
                    }}></div>
                    <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.06)',
                      animation: 'randomPulse 3.2s ease-in-out infinite',
                      animationDelay: '2.4s'
                    }}></div>
                    <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.11)',
                      animation: 'randomPulse 2.4s ease-in-out infinite',
                      animationDelay: '0.9s'
                    }}></div>
                    <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.05)',
                      animation: 'randomPulse 3.8s ease-in-out infinite',
                      animationDelay: '1.7s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.09)',
                      animation: 'randomPulse 2.7s ease-in-out infinite',
                      animationDelay: '1.1s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.07)',
                      animation: 'randomPulse 3.9s ease-in-out infinite',
                      animationDelay: '2.6s'
                    }}></div>
                  </div>
                  
                  {/* Animated Lines */}
                  <div className="absolute inset-0">
                    <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                    <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                  </div>
                </div>
              </Card>

              <Card className="p-4 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
                <div className="flex items-center justify-between relative z-10">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t('documentsPage.total_chunks')}</p>
                    <p className="text-2xl font-bold text-muted-foreground">{stats.total_chunks}</p>
                  </div>
                  <div className="relative -mt-5">
                    <FileIcon className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                      style={{
                        '--hover-color': 'rgb(var(--card-hover-icon))'
                      } as React.CSSProperties}
                      onMouseEnter={(e) => {
                        (e.target as HTMLElement).style.color = 'var(--hover-color)';
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLElement).style.color = '';
                      }}
                    />
                  </div>
                </div>
                
                {/* Shine Effect */}
                <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                  <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                       style={{
                         background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                       }}>
                  </div>
                </div>
                
                {/* Animated Background */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                     style={{
                       maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                       WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                     }}>
                  
                  {/* Animated Tiles */}
                  <div className="absolute inset-0">
                    <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.07)',
                      animation: 'randomPulse 3.1s ease-in-out infinite',
                      animationDelay: '0.8s'
                    }}></div>
                    <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.11)',
                      animation: 'randomPulse 2.6s ease-in-out infinite',
                      animationDelay: '1.6s'
                    }}></div>
                    <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.05)',
                      animation: 'randomPulse 4.3s ease-in-out infinite',
                      animationDelay: '0.1s'
                    }}></div>
                    <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.09)',
                      animation: 'randomPulse 3.7s ease-in-out infinite',
                      animationDelay: '2.2s'
                    }}></div>
                    <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.04)',
                      animation: 'randomPulse 2.9s ease-in-out infinite',
                      animationDelay: '1.0s'
                    }}></div>
                    <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.12)',
                      animation: 'randomPulse 3.3s ease-in-out infinite',
                      animationDelay: '2.8s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.08)',
                      animation: 'randomPulse 4.1s ease-in-out infinite',
                      animationDelay: '0.4s'
                    }}></div>
                    <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                      background: 'rgb(var(--card-effect-primary) / 0.06)',
                      animation: 'randomPulse 2.4s ease-in-out infinite',
                      animationDelay: '1.8s'
                    }}></div>
                  </div>
                  
                  {/* Animated Lines */}
                  <div className="absolute inset-0">
                    <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                    <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                    <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* Tabs para as diferentes áreas */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6 bg-gradient-to-br from-card to-card/45 border border-border h-auto min-h-[3rem]">
              <TabsTrigger value="knowledge-base" className="flex items-center justify-center gap-2 h-full">
                <FileText className="h-4 w-4" />
                {t('documentsPage.knowledge_base')}
              </TabsTrigger>
              <TabsTrigger value="useful-links" className="flex items-center justify-center gap-2 h-full">
                <LinkIcon className="h-4 w-4" />
                {t('documentsPage.useful_links')}
              </TabsTrigger>
              <TabsTrigger value="downloadable-docs" className="flex items-center justify-center gap-2 h-full">
                <Download className="h-4 w-4" />
                {t('documentsPage.forms_and_docs')}
              </TabsTrigger>
            </TabsList>

            {/* Base de Conhecimento */}
            <TabsContent value="knowledge-base" className="space-y-0">
              {error ? (
                <Card className="p-8 text-center">
                  <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                  <p className="text-destructive mb-2">{t('documentsPage.error_loading_documents')}</p>
                  <p className="text-muted-foreground text-sm">
                    {t('documentsPage.check_auth_permissions')}
                  </p>
                </Card>
              ) : isLoading ? (
                <Card className="p-8 text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
                </Card>
              ) : documents && documents.length > 0 ? (
                <DataTable
                  columns={documentColumns}
                  data={documents}
                  searchKey="title"
                  searchPlaceholder={t('documentsPage.search_documents')}
                  actionButton={
                    <Button onClick={() => setUploadDialogOpen(true)} className="flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      {t('documentsPage.upload_document')}
                    </Button>
                  }
                />
              ) : (
                <div className="space-y-0">
                  <div className="flex items-center justify-end mb-6">
                    <Button onClick={() => setUploadDialogOpen(true)} className="flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      {t('documentsPage.upload_document')}
                    </Button>
                  </div>
                  <Card className="p-8 text-center">
                    <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">{t('documentsPage.no_documents_found')}</p>
                  </Card>
                </div>
              )}
            </TabsContent>

            {/* Links Úteis */}
            <TabsContent value="useful-links" className="space-y-0">
              {linksError ? (
                <Card className="p-8 text-center">
                  <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                  <p className="text-destructive mb-2">{t('documentsPage.error_loading_links')}</p>
                  <p className="text-muted-foreground text-sm">
                    {t('documentsPage.check_connection_try_again')}
                  </p>
                </Card>
              ) : linksLoading ? (
                <Card className="p-8 text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
                </Card>
              ) : usefulLinks && usefulLinks.length > 0 ? (
                <DataTable
                  columns={usefulLinksColumns}
                  data={usefulLinks}
                  searchKey="title"
                  searchPlaceholder={t('documentsPage.search_documents')}
                  actionButton={
                    <Button onClick={() => handleOpenLinkDialog()} className="flex items-center gap-2">
                      <Plus className="h-4 w-4" />
                      {t('documentsPage.add_link')}
                    </Button>
                  }
                />
              ) : (
                <div className="space-y-0">
                  <div className="flex items-center justify-end mb-6">
                    <Button onClick={() => handleOpenLinkDialog()} className="flex items-center gap-2">
                      <Plus className="h-4 w-4" />
                      {t('documentsPage.add_link')}
                    </Button>
                  </div>
                  <Card className="p-8 text-center">
                    <LinkIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">{t('documentsPage.no_links_found')}</p>
                  </Card>
                </div>
              )}
            </TabsContent>

            {/* Documentos para Download */}
            <TabsContent value="downloadable-docs" className="space-y-0">
              {docsError ? (
                <Card className="p-8 text-center">
                  <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                  <p className="text-destructive mb-2">{t('documentsPage.error_loading_documents')}</p>
                  <p className="text-muted-foreground text-sm">
                    {t('documentsPage.check_connection_try_again')}
                  </p>
                </Card>
              ) : docsLoading ? (
                <Card className="p-8 text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
                </Card>
              ) : downloadableDocuments && downloadableDocuments.length > 0 ? (
                <DataTable
                  columns={downloadableDocumentsColumns}
                  data={downloadableDocuments}
                  searchKey="title"
                  searchPlaceholder={t('documentsPage.search_documents')}
                  actionButton={
                    <Button onClick={() => handleOpenDownloadableDocDialog()} className="flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      {t('documentsPage.upload_document')}
                    </Button>
                  }
                />
              ) : (
                <div className="space-y-0">
                  <div className="flex items-center justify-end mb-6">
                    <Button onClick={() => handleOpenDownloadableDocDialog()} className="flex items-center gap-2">
                      <Upload className="h-4 w-4" />
                      {t('documentsPage.upload_document')}
                    </Button>
                  </div>
                  <Card className="p-8 text-center">
                    <FileIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">{t('documentsPage.no_documents_found')}</p>
                  </Card>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Upload Dialog */}
      {uploadDialogOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-gradient-to-br from-background via-background/95 to-background/90 rounded-xl max-w-md w-full p-6 border border-border/30 shadow-xl">
            <h2 className="text-xl font-semibold text-foreground mb-4">
              {t('documentsPage.upload_document_modal')}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.file')}
                </label>
                <input
                  type="file"
                  onChange={handleFileSelect}
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md"
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('documentsPage.file_types_supported')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.document_title')}
                </label>
                <input
                  type="text"
                  value={documentTitle}
                  onChange={(e) => setDocumentTitle(e.target.value)}
                  placeholder={t('documentsPage.type_document_title')}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground"
                />
              </div>

            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setUploadDialogOpen(false);
                  resetUploadForm();
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? t('documentsPage.sending') : t('documentsPage.send')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* View Content Dialog - continua igual mas com tema atualizado */}
      {viewDialogOpen && selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-background rounded-lg max-w-4xl w-full h-[80vh] flex flex-col">
            <div className="p-6 border-b border-border">
              <h2 className="text-xl font-semibold text-foreground">
                {selectedDocument.title}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                {t('documentsPage.markdown_content')}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
              <pre className="whitespace-pre-wrap text-sm text-foreground font-mono">
                {documentContent}
              </pre>
            </div>

            <div className="p-6 border-t border-border flex justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setViewDialogOpen(false);
                  setDocumentContent('');
                  setSelectedDocument(null);
                }}
              >
                {t('common.close')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog - continua igual mas com tema atualizado */}
      {deleteDialogOpen && selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-background rounded-lg max-w-md w-full p-6">
            <h2 className="text-xl font-semibold text-foreground mb-4">
              {t('documentsPage.confirm_deletion')}
            </h2>
            <p className="text-muted-foreground mb-6">
              {t('documentsPage.confirm_delete_document', { title: selectedDocument.title })}
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteDialogOpen(false);
                  setSelectedDocument(null);
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                variant="destructive"
                onClick={() => {
                  if (selectedDocument) {
                    deleteMutation.mutate(selectedDocument.id);
                  }
                }}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? t('documentsPage.deleting') : t('documentsPage.delete')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Links Úteis */}
      {linkDialogOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-gradient-to-br from-background via-background/95 to-background/90 rounded-xl max-w-2xl w-full p-6 border border-border/30 shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-foreground mb-4">
              {editingLink ? t('documentsPage.edit_useful_link') : t('documentsPage.add_useful_link')}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.link_title')}
                </label>
                <Input
                  type="text"
                  value={linkTitle}
                  onChange={(e) => setLinkTitle(e.target.value)}
                  placeholder={t('documentsPage.link_title_placeholder')}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.url')}
                </label>
                <Input
                  type="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder={t('documentsPage.url_placeholder')}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.category')}
                </label>
                <Select
                  value={linkCategory}
                  onValueChange={setLinkCategory}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Selecione uma categoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map(category => (
                      <SelectItem key={category.id} value={category.name}>
                        {category.name}
                      </SelectItem>
                    ))}
                    <SelectItem value="__create_new__">
                      <span className="text-muted-foreground">+ Criar nova categoria</span>
                    </SelectItem>
                  </SelectContent>
                </Select>

                {linkCategory === '__create_new__' && (
                  <div className="mt-2">
                    <Input
                      type="text"
                      value={newCategoryName}
                      onChange={(e) => setNewCategoryName(e.target.value)}
                      placeholder="Digite o nome da nova categoria"
                      className="w-full"
                      onBlur={() => {
                        if (newCategoryName.trim()) {
                          setLinkCategory(newCategoryName.trim());
                          setNewCategoryName('');
                        }
                      }}
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.link_description')}
                </label>
                <textarea
                  value={linkDescription}
                  onChange={(e) => setLinkDescription(e.target.value)}
                  placeholder={t('documentsPage.link_description_placeholder')}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground min-h-[80px] resize-y"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('documentsPage.link_description_help')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.ai_guidance')}
                </label>
                <textarea
                  value={linkAiGuidance}
                  onChange={(e) => setLinkAiGuidance(e.target.value)}
                  placeholder={t('documentsPage.ai_guidance_placeholder')}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground min-h-[100px] resize-y"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('documentsPage.ai_guidance_help')}
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setLinkDialogOpen(false);
                  resetLinkForm();
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSaveLink}
                disabled={!linkTitle || !linkUrl || createLinkMutation.isPending || updateLinkMutation.isPending}
              >
                {createLinkMutation.isPending || updateLinkMutation.isPending ?
                  t('documentsPage.saving') :
                  (editingLink ? t('documentsPage.update') : t('common.save'))
                }
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Documentos Baixáveis */}
      {downloadableDocDialogOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-gradient-to-br from-background via-background/95 to-background/90 rounded-xl max-w-2xl w-full p-6 border border-border/30 shadow-xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-foreground mb-4">
              {editingDownloadableDoc ? t('documentsPage.edit_document') : t('documentsPage.add_downloadable_document')}
            </h2>

            <div className="space-y-4">
              {!editingDownloadableDoc && (
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    {t('documentsPage.file')}
                  </label>
                  <input
                    type="file"
                    onChange={handleDownloadableDocFileSelect}
                    accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md"
                    className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t('documentsPage.file_types_supported')}
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.document_title')}
                </label>
                <Input
                  type="text"
                  value={downloadableDocTitle}
                  onChange={(e) => setDownloadableDocTitle(e.target.value)}
                  placeholder={t('documentsPage.document_title_placeholder')}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.category')}
                </label>
                <Select
                  value={downloadableDocCategory}
                  onValueChange={setDownloadableDocCategory}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Selecione uma categoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map(category => (
                      <SelectItem key={category.id} value={category.name}>
                        {category.name}
                      </SelectItem>
                    ))}
                    <SelectItem value="__create_new__">
                      <span className="text-muted-foreground">+ Criar nova categoria</span>
                    </SelectItem>
                  </SelectContent>
                </Select>

                {downloadableDocCategory === '__create_new__' && (
                  <div className="mt-2">
                    <Input
                      type="text"
                      value={newCategoryName}
                      onChange={(e) => setNewCategoryName(e.target.value)}
                      placeholder="Digite o nome da nova categoria"
                      className="w-full"
                      onBlur={() => {
                        if (newCategoryName.trim()) {
                          setDownloadableDocCategory(newCategoryName.trim());
                          setNewCategoryName('');
                        }
                      }}
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.document_description')}
                </label>
                <textarea
                  value={downloadableDocDescription}
                  onChange={(e) => setDownloadableDocDescription(e.target.value)}
                  placeholder={t('documentsPage.document_description_placeholder')}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground min-h-[80px] resize-y"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('documentsPage.document_description_help')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {t('documentsPage.ai_guidance')}
                </label>
                <textarea
                  value={downloadableDocAiGuidance}
                  onChange={(e) => setDownloadableDocAiGuidance(e.target.value)}
                  placeholder={t('documentsPage.ai_guidance_docs_placeholder')}
                  className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent bg-background text-foreground min-h-[100px] resize-y"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t('documentsPage.ai_guidance_docs_help')}
                </p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setDownloadableDocDialogOpen(false);
                  resetDownloadableDocForm();
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSaveDownloadableDoc}
                disabled={!downloadableDocTitle || (!downloadableDocFile && !editingDownloadableDoc) || createDownloadableDocMutation.isPending || updateDownloadableDocMutation.isPending}
              >
                {createDownloadableDocMutation.isPending || updateDownloadableDocMutation.isPending ?
                  t('documentsPage.saving') :
                  (editingDownloadableDoc ? t('documentsPage.update') : t('common.save'))
                }
              </Button>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  );
};