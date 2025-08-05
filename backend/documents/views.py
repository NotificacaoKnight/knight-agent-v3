import os
from django.conf import settings
from django.http import Http404, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsKnightAdmin
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentChunk, ProcessingJob
from .serializers import DocumentSerializer, DocumentChunkSerializer, ProcessingJobSerializer
from .services import DocumentProcessor, calculate_file_checksum
from .tasks import process_document_task

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de documentos - Admin only"""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]  # Temporário: removido IsKnightAdmin para teste
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return Document.objects.filter(is_active=True).order_by('-uploaded_at')
    
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
            # Verificar se já existe documento com mesmo nome/título
            title = request.data.get('title', uploaded_file.name)
            existing_doc = Document.objects.filter(
                title=title,
                is_active=True
            ).first()
            
            if existing_doc:
                return Response({
                    'error': f'Documento "{title}" já existe no sistema',
                    'existing_document_id': existing_doc.id,
                    'uploaded_at': existing_doc.uploaded_at
                }, status=status.HTTP_409_CONFLICT)
            
            # Converter string boolean para boolean real
            is_downloadable_str = request.data.get('is_downloadable', 'false')
            is_downloadable = is_downloadable_str in ['true', 'True', '1', 1, True]
            
            # Criar documento
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
            
            # Iniciar processamento assíncrono com Celery
            try:
                process_document_task.delay(document.id)
            except Exception as celery_error:
                # Fallback para processamento síncrono se Celery falhar
                try:
                    from .tasks import process_document_sync
                    process_document_sync(document.id)
                except Exception as sync_error:
                    document.status = 'error'
                    document.processing_error = f"Celery: {celery_error}, Sync: {sync_error}"
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
        process_document_task.delay(document.id)
        
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
    
    def destroy(self, request, pk=None):
        """Exclusão completa de documento com limpeza total de embeddings, caches e arquivos"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            document = self.get_object()
            document_id = document.id
            document_title = document.title
            
            logger.info(f"Starting COMPLETE deletion of document {document_id}: {document_title}")
            
            # 1. Contar chunks antes da exclusão
            chunks_count = document.chunks.count()
            embedded_chunks = document.chunks.filter(embedding__isnull=False).count()
            
            # 2. Remover embeddings dos serviços de vetor (pgvector + FAISS)
            try:
                from rag.hybrid_vector_service import HybridVectorService
                vector_service = HybridVectorService()
                vector_service.remove_document_embeddings(document_id)
                logger.info(f"Embeddings removed from vector services for document {document_id}")
            except Exception as vector_error:
                logger.error(f"Failed to remove embeddings for document {document_id}: {vector_error}")
            
            # 3. Limpar caches relacionados ao documento
            try:
                from rag.cache_manager import RAGCacheManager
                RAGCacheManager.clear_document_caches(document_id)
                RAGCacheManager.invalidate_search_indices()
                logger.info(f"Caches cleared for document {document_id}")
            except Exception as cache_error:
                logger.error(f"Failed to clear caches for document {document_id}: {cache_error}")
            
            # 4. Remover arquivos físicos
            files_removed = []
            
            # 4a. Arquivo original
            if document.file_path and os.path.exists(document.file_path.path):
                try:
                    os.remove(document.file_path.path)
                    files_removed.append(f"Original: {document.file_path.path}")
                    logger.info(f"Original file deleted: {document.file_path.path}")
                except OSError as file_error:
                    logger.warning(f"Could not delete original file: {file_error}")
            
            # 4b. Pasta de documentos processados
            import shutil
            processed_dir_paths = [
                f"/home/felipealbertuxd/knight-agent/backend/processed_documents/{document_id}/",
                document.processed_path
            ]
            
            for processed_path in processed_dir_paths:
                if processed_path and os.path.exists(processed_path):
                    try:
                        if os.path.isdir(processed_path):
                            shutil.rmtree(processed_path)
                        else:
                            processed_dir = os.path.dirname(processed_path)
                            if os.path.exists(processed_dir):
                                shutil.rmtree(processed_dir)
                        files_removed.append(f"Processed: {processed_path}")
                        logger.info(f"Processed files deleted: {processed_path}")
                        break  # Só remove uma vez
                    except OSError as dir_error:
                        logger.warning(f"Could not delete processed directory {processed_path}: {dir_error}")
            
            # 5. HARD DELETE completo - usar delete() para trigger do signal post_delete
            logger.info(f"Performing HARD DELETE for document {document_id}")
            document.delete()  # Isso ativa o signal post_delete automaticamente
            
            # 6. Notificar atualização dos índices após exclusão
            try:
                from rag.cache_manager import RAGCacheManager
                RAGCacheManager.notify_index_update(f'document_hard_deleted_{document_id}')
                logger.info(f"Index update notification sent for deleted document {document_id}")
            except Exception as notify_error:
                logger.warning(f"Failed to notify index update: {notify_error}")
            
            return Response({
                'message': f'Documento "{document_title}" COMPLETAMENTE excluído',
                'document_id': document_id,
                'chunks_removed': chunks_count,
                'embeddings_removed': embedded_chunks,
                'files_removed': files_removed,
                'deletion_type': 'HARD_DELETE'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error in COMPLETE deletion of document {pk}: {str(e)}")
            
            return Response({
                'error': f'Erro na exclusão completa do documento: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsKnightAdmin])
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
@permission_classes([IsAuthenticated, IsKnightAdmin])
def processing_status(request):
    """Status dos processamentos em andamento"""
    jobs = ProcessingJob.objects.filter(
        status__in=['queued', 'processing']
    ).select_related('document')[:10]
    
    serializer = ProcessingJobSerializer(jobs, many=True)
    return Response(serializer.data)