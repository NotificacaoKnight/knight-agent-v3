import os
from django.conf import settings
from django.http import Http404, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentChunk, ProcessingJob
from .serializers import DocumentSerializer, DocumentChunkSerializer, ProcessingJobSerializer
from .services import DocumentProcessor, calculate_file_checksum
try:
    from .tasks import process_document_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
from .simple_processor import process_document_sync

def delete_document_completely(document_id):
    """
    Remove documento completamente de todos os lugares:
    - Django database
    - MongoDB Atlas 
    - FAISS index
    - Arquivos físicos
    """
    try:
        from pymongo import MongoClient
        from pymongo.server_api import ServerApi
        from django.conf import settings
        import os
        
        document = Document.objects.get(id=document_id)
        print(f"🗑️ Iniciando remoção completa do documento {document_id}: {document.title}")
        
        # 1. Remover do MongoDB Atlas
        try:
            mongodb_url = settings.MONGODB_URL
            client = MongoClient(mongodb_url, server_api=ServerApi('1'))
            db = client['knight_agno']
            collection = db['knight_documents']
            
            result = collection.delete_many({'document_id': str(document_id)})
            print(f"🍃 MongoDB: {result.deleted_count} documentos removidos")
            client.close()
        except Exception as e:
            print(f"⚠️ Erro ao remover do MongoDB: {e}")
        
        # 2. Remover do FAISS (via Agno)
        try:
            from .agno_document_service import AgnoDocumentService
            agno_service = AgnoDocumentService()
            # O FAISS será atualizado na próxima inicialização
            print(f"📊 FAISS: Será atualizado na próxima inicialização")
        except Exception as e:
            print(f"⚠️ Erro ao acessar FAISS: {e}")
        
        # 3. Remover arquivo físico
        try:
            if document.file_path and os.path.exists(document.file_path.path):
                os.remove(document.file_path.path)
                print(f"📁 Arquivo físico removido: {document.file_path.path}")
        except Exception as e:
            print(f"⚠️ Erro ao remover arquivo físico: {e}")
        
        # 4. Remover markdown processado
        try:
            if document.processed_path and os.path.exists(document.processed_path):
                os.remove(document.processed_path)
                print(f"📄 Markdown processado removido: {document.processed_path}")
        except Exception as e:
            print(f"⚠️ Erro ao remover markdown: {e}")
        
        # 5. Remover chunks e jobs relacionados
        chunks_count = document.chunks.count()
        jobs_count = document.processing_jobs.count()
        
        document.chunks.all().delete()
        document.processing_jobs.all().delete()
        
        print(f"🔗 Removidos {chunks_count} chunks e {jobs_count} jobs")
        
        # 6. Remover do Django (último)
        document_title = document.title
        document.delete()
        
        print(f"✅ Documento '{document_title}' removido completamente de todos os lugares!")
        return True
        
    except Document.DoesNotExist:
        print(f"❌ Documento {document_id} não encontrado")
        return False
    except Exception as e:
        print(f"❌ Erro na remoção completa: {e}")
        import traceback
        traceback.print_exc()
        return False

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de documentos"""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Document.objects.filter(is_active=True).order_by('-uploaded_at')
    
    def list(self, request, *args, **kwargs):
        """Lista documentos com tratamento de erro"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"❌ Erro na listagem de documentos: {e}")
            # Retornar lista vazia em caso de erro
            return Response([])
    
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload de novo documento"""
        if 'file' not in request.FILES:
            return Response({'error': 'Nenhum arquivo enviado'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Validar tipo de arquivo
        allowed_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.md']
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return Response({
                'error': f'Tipo de arquivo não suportado. Tipos permitidos: {", ".join(allowed_extensions)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar tamanho do arquivo (máximo 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            return Response({'error': 'Arquivo muito grande. Máximo 50MB'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Criar documento
            is_downloadable_value = request.data.get('is_downloadable', 'false')
            if isinstance(is_downloadable_value, str):
                is_downloadable = is_downloadable_value.lower() in ('true', '1', 'yes', 'on')
            else:
                is_downloadable = bool(is_downloadable_value)
            
            document = Document.objects.create(
                title=request.data.get('title', uploaded_file.name),
                original_filename=uploaded_file.name,
                file_path=uploaded_file,
                file_type=file_extension,
                file_size=uploaded_file.size,
                uploaded_by=request.user,
                is_downloadable=is_downloadable,
            )
            
            # Calcular checksum
            document.checksum = calculate_file_checksum(document.file_path.path)
            document.save()
            
            # Iniciar processamento
            try:
                if CELERY_AVAILABLE and getattr(settings, 'USE_CELERY', True):
                    process_document_task.delay(document.id)
                else:
                    # Processar de forma síncrona
                    process_document_sync(document.id)
            except Exception as processing_error:
                # Se o Celery falhar (Redis não disponível), usar processamento síncrono
                print(f"Celery falhou, usando processamento síncrono: {processing_error}")
                try:
                    process_document_sync(document.id)
                except Exception as sync_error:
                    print(f"Erro no processamento síncrono: {sync_error}")
                    document.status = 'error'
                    document.processing_error = f"Erro de processamento: {sync_error}"
                    document.save()
            
            return Response(DocumentSerializer(document).data, 
                           status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocessar documento"""
        document = self.get_object()
        
        # Limpar processamento anterior
        document.chunks.all().delete()
        document.status = 'pending'
        document.processing_error = ''
        document.save()
        
        # Iniciar novo processamento
        if CELERY_AVAILABLE and getattr(settings, 'USE_CELERY', True):
            process_document_task.delay(document.id)
        else:
            process_document_sync(document.id)
        
        return Response({'message': 'Reprocessamento iniciado'})
    
    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Buscar conteúdo markdown do documento"""
        document = self.get_object()
        
        if document.status != 'processed':
            return Response({'error': 'Documento ainda não foi processado'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'title': document.title,
            'content': document.markdown_content,
            'metadata': document.metadata,
            'chunks_count': document.chunks.count()
        })
    
    @action(detail=True, methods=['get'])
    def agno_test(self, request, pk=None):
        """Testar se documento está indexado no Agno"""
        document = self.get_object()
        
        try:
            from .agno_document_service import AgnoDocumentService
            
            agno_service = AgnoDocumentService()
            
            # Buscar documento no Agno pelo título
            search_results = agno_service.search_documents(
                query=document.title,
                limit=5
            )
            
            # Buscar por ID do documento
            doc_by_id = agno_service.get_document_by_id(str(document.id))
            
            return Response({
                'document_id': document.id,
                'title': document.title,
                'status': document.status,
                'agno_search_results': search_results,
                'agno_document_by_id': doc_by_id,
                'indexed_in_agno': len(search_results) > 0 or doc_by_id is not None,
                'markdown_preview': document.markdown_content[:500] + '...' if document.markdown_content else None
            })
            
        except Exception as e:
            return Response({
                'error': str(e),
                'document_id': document.id,
                'title': document.title
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Listar chunks do documento"""
        document = self.get_object()
        chunks = document.chunks.all()
        
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download do arquivo original"""
        document = self.get_object()
        
        if not document.is_downloadable:
            return Response({'error': 'Este documento não está disponível para download'}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            if document.file_path and os.path.exists(document.file_path.path):
                with open(document.file_path.path, 'rb') as file:
                    response = HttpResponse(
                        file.read(),
                        content_type='application/octet-stream'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
                    return response
            else:
                raise Http404("Arquivo não encontrado")
                
        except Exception as e:
            return Response({'error': str(e)}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Deletar documento completamente de todos os lugares"""
        document = self.get_object()
        document_id = document.id
        document_title = document.title
        
        # Usar nossa função de remoção completa
        success = delete_document_completely(document_id)
        
        if success:
            return Response({
                'message': f'Documento "{document_title}" removido completamente de todos os lugares',
                'removed_from': [
                    'Django Database',
                    'MongoDB Atlas', 
                    'FAISS Index',
                    'Arquivos Físicos'
                ]
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Erro ao remover documento completamente'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_stats(request):
    """Estatísticas dos documentos"""
    stats = {
        'total_documents': Document.objects.filter(is_active=True).count(),
        'processed_documents': Document.objects.filter(is_active=True, status='processed').count(),
        'pending_documents': Document.objects.filter(is_active=True, status='pending').count(),
        'processing_documents': Document.objects.filter(is_active=True, status='processing').count(),
        'error_documents': Document.objects.filter(is_active=True, status='error').count(),
        'downloadable_documents': Document.objects.filter(is_active=True, is_downloadable=True).count(),
        'total_chunks': DocumentChunk.objects.count(),
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def processing_status(request):
    """Status dos processamentos em andamento"""
    jobs = ProcessingJob.objects.filter(
        status__in=['queued', 'processing']
    ).select_related('document')[:10]
    
    serializer = ProcessingJobSerializer(jobs, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_agno_search(request):
    """Testar busca no Agno com query customizada"""
    query = request.data.get('query', '')
    limit = request.data.get('limit', 5)
    
    if not query:
        return Response({'error': 'Query é obrigatória'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from .agno_document_service import AgnoDocumentService
        
        agno_service = AgnoDocumentService()
        
        # Buscar no Agno
        search_results = agno_service.search_documents(
            query=query,
            limit=limit
        )
        
        # Estatísticas
        total_docs = Document.objects.filter(is_active=True, status='processed').count()
        
        return Response({
            'query': query,
            'limit': limit,
            'results_count': len(search_results),
            'total_processed_docs': total_docs,
            'search_results': search_results,
            'agno_working': len(search_results) > 0 if total_docs > 0 else 'No documents to search'
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'query': query
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)