import os
import shutil
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete
from django.dispatch import receiver
from pgvector.django import VectorField

User = get_user_model()

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('processed', 'Processado'),
        ('error', 'Erro'),
    ]
    
    title = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='documents/')
    processed_path = models.CharField(max_length=500, blank=True)
    markdown_content = models.TextField(blank=True)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    checksum = models.CharField(max_length=64)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True)
    
    is_downloadable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadados extraídos
    metadata = models.JSONField(default=dict, blank=True)
    
    # Contador de acessos para ranking
    access_count = models.IntegerField(default=0, help_text="Número de vezes que o documento foi acessado no RAG")
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    
    # pgvector field - BGE-m3 uses 1024 dimensions
    embedding = VectorField(dimensions=1024, null=True, blank=True)
    
    # Keep JSON backup for compatibility during migration
    embedding_json = models.JSONField(null=True, blank=True)
    
    chunk_size = models.IntegerField()
    start_position = models.IntegerField(default=0)
    end_position = models.IntegerField(default=0)
    
    # Metadados do chunk
    page_number = models.IntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
        indexes = [
            # Vector similarity index will be created via migration
            # Using raw SQL for better control over index parameters
        ]
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

class ProcessingJob(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Na Fila'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhado'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_jobs')
    job_type = models.CharField(max_length=50)  # 'markdown_conversion', 'chunking', 'embedding'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Configurações do job
    config = models.JSONField(default=dict, blank=True)
    
    # Resultados
    result = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.title} - {self.job_type} ({self.status})"


@receiver(post_delete, sender=Document)
def cleanup_document_files(sender, instance, **kwargs):
    """Limpeza COMPLETA após exclusão do documento - arquivos, embeddings, caches e índices"""
    import logging
    logger = logging.getLogger('documents.cleanup')
    
    try:
        doc_id = instance.id
        doc_title = instance.title
        logger.info(f"Starting COMPLETE cleanup for deleted document {doc_id}: {doc_title}")
        
        files_cleaned = []
        
        # 1. Remover arquivo original
        if instance.file_path:
            try:
                # Tentar com caminho absoluto primeiro
                file_path = instance.file_path.path if hasattr(instance.file_path, 'path') else str(instance.file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_cleaned.append(f"Original: {file_path}")
                    logger.info(f"Original file removed: {file_path}")
            except Exception as file_error:
                logger.warning(f"Could not remove original file: {file_error}")
        
        # 2. Remover pasta processada - múltiplas tentativas
        processed_paths_to_try = [
            instance.processed_path,
            f"/home/felipealbertuxd/knight-agent/backend/processed_documents/{doc_id}/",
            f"processed_documents/{doc_id}/"
        ]
        
        for processed_path in processed_paths_to_try:
            if not processed_path:
                continue
                
            try:
                # Se é um arquivo, pegar a pasta pai
                if processed_path.endswith('.md'):
                    processed_dir = os.path.dirname(processed_path)
                else:
                    processed_dir = processed_path
                
                if os.path.exists(processed_dir):
                    shutil.rmtree(processed_dir)
                    files_cleaned.append(f"Processed: {processed_dir}")
                    logger.info(f"Processed directory removed: {processed_dir}")
                    break  # Só remove uma vez
                    
            except Exception as dir_error:
                logger.warning(f"Could not remove processed directory {processed_path}: {dir_error}")
        
        # 3. Limpeza COMPLETA de embeddings e caches
        try:
            # 3a. Usar HybridVectorService para limpeza completa
            try:
                from rag.hybrid_vector_service import HybridVectorService
                hybrid_service = HybridVectorService()
                hybrid_service.remove_document_embeddings(doc_id)
                logger.info(f"Embeddings removed from ALL vector services for document {doc_id}")
            except Exception as hybrid_error:
                logger.error(f"HybridVectorService cleanup failed: {hybrid_error}")
                
                # Fallback: tentar serviços individuais
                from django.conf import settings
                
                # Tentar pgvector
                if getattr(settings, 'USE_PGVECTOR', False):
                    try:
                        from rag.pgvector_service import PgVectorSearchService
                        pgvector_service = PgVectorSearchService()
                        pgvector_service.remove_document_embeddings(doc_id)
                        logger.info(f"pgvector embeddings removed for document {doc_id}")
                    except Exception as pgv_error:
                        logger.warning(f"pgvector cleanup failed: {pgv_error}")
                
                # Tentar FAISS
                try:
                    from rag.services import VectorSearchService
                    vector_service = VectorSearchService()
                    if hasattr(vector_service, 'remove_document_embeddings'):
                        vector_service.remove_document_embeddings(doc_id)
                        logger.info(f"FAISS embeddings removed for document {doc_id}")
                except Exception as faiss_error:
                    logger.warning(f"FAISS cleanup failed: {faiss_error}")
            
            # 3b. Limpar todos os caches relacionados
            try:
                from rag.cache_manager import RAGCacheManager
                
                # Limpar caches do documento
                RAGCacheManager.clear_document_caches(doc_id)
                
                # Invalidar TODOS os índices de busca
                RAGCacheManager.invalidate_search_indices()
                
                # Forçar limpeza de cache de embeddings (se existir)
                if hasattr(RAGCacheManager, 'clear_embedding_cache'):
                    RAGCacheManager.clear_embedding_cache(doc_id)
                
                # Notificar sistemas dependentes
                RAGCacheManager.notify_index_update(f'complete_document_deletion_{doc_id}')
                
                logger.info(f"ALL caches and indices invalidated for document {doc_id}")
                
            except Exception as cache_error:
                logger.error(f"Cache cleanup failed for document {doc_id}: {cache_error}")
            
        except Exception as vector_error:
            logger.error(f"Vector store cleanup failed for document {doc_id}: {vector_error}")
        
        # 4. Log final da limpeza
        logger.info(f"COMPLETE cleanup finished for document {doc_id}. Files cleaned: {files_cleaned}")
        print(f"✅ LIMPEZA COMPLETA do documento {doc_id}: {len(files_cleaned)} arquivos removidos")
        
    except Exception as e:
        logger.error(f"CRITICAL: Complete cleanup failed for document {getattr(instance, 'id', 'unknown')}: {e}")
        print(f"❌ Erro crítico na limpeza completa: {e}")