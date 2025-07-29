import os
from datetime import datetime
from django.conf import settings
from celery import shared_task
from .models import Document, DocumentChunk, ProcessingJob
from .services import DocumentProcessor
from rag.services import EmbeddingService, ChunkingService

@shared_task
def process_document_task(document_id):
    """Task assíncrona para processar documento"""
    try:
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        
        # Criar job de processamento
        job = ProcessingJob.objects.create(
            document=document,
            job_type='full_processing',
            status='processing',
            started_at=datetime.now()
        )
        
        # Inicializar serviços
        processor = DocumentProcessor()
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService()
        
        # Criar diretório de saída
        output_dir = os.path.join(settings.PROCESSED_DOCS_PATH, str(document.id))
        os.makedirs(output_dir, exist_ok=True)
        
        # Etapa 1: Conversão para markdown
        result = processor.process_document(
            document.file_path.path,
            output_dir
        )
        
        if not result['success']:
            raise Exception(f"Erro na conversão: {result['error']}")
        
        # Salvar conteúdo markdown
        document.markdown_content = result['markdown_content']
        document.processed_path = result['output_path']
        document.metadata = result['metadata']
        document.save()
        
        # Etapa 2: Chunking
        chunks = chunking_service.create_chunks(
            result['markdown_content'],
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )
        
        # Salvar chunks no banco
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_obj = DocumentChunk(
                document=document,
                chunk_index=i,
                content=chunk['content'],
                chunk_size=len(chunk['content']),
                start_position=chunk.get('start', 0),
                end_position=chunk.get('end', len(chunk['content'])),
                page_number=chunk.get('page_number'),
                section_title=chunk.get('section_title', '')
            )
            chunk_objects.append(chunk_obj)
        
        DocumentChunk.objects.bulk_create(chunk_objects)
        
        # Etapa 3: Gerar embeddings
        embedding_service.generate_embeddings_for_document(document)
        
        # Finalizar processamento
        document.status = 'processed'
        document.processed_at = datetime.now()
        document.save()
        
        job.status = 'completed'
        job.completed_at = datetime.now()
        job.result = {
            'chunks_created': len(chunk_objects),
            'markdown_length': len(result['markdown_content']),
            'metadata': result['metadata']
        }
        job.save()
        
        return {
            'success': True,
            'document_id': document.id,
            'chunks_created': len(chunk_objects)
        }
        
    except Exception as e:
        # Atualizar status de erro
        document.status = 'error'
        document.processing_error = str(e)
        document.save()
        
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = datetime.now()
        job.save()
        
        return {
            'success': False,
            'error': str(e),
            'document_id': document.id
        }

def process_document_sync(document_id):
    """Versão síncrona do processamento de documento (sem Celery)"""
    try:
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        
        # Criar job de processamento
        job = ProcessingJob.objects.create(
            document=document,
            job_type='full_processing',
            status='processing',
            started_at=datetime.now()
        )
        
        # Inicializar serviços
        processor = DocumentProcessor()
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService()
        
        # Criar diretório de saída
        output_dir = os.path.join(settings.PROCESSED_DOCS_PATH, str(document.id))
        os.makedirs(output_dir, exist_ok=True)
        
        # Etapa 1: Conversão para markdown
        result = processor.process_document(
            document.file_path.path,
            output_dir
        )
        
        if not result['success']:
            raise Exception(f"Erro na conversão: {result['error']}")
        
        # Salvar conteúdo markdown
        document.markdown_content = result['markdown_content']
        document.processed_path = result['output_path']
        document.metadata = result['metadata']
        document.save()
        
        # Etapa 2: Chunking
        chunks = chunking_service.create_chunks(
            result['markdown_content'],
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP
        )
        
        # Salvar chunks no banco
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_obj = DocumentChunk(
                document=document,
                chunk_index=i,
                content=chunk['content'],
                chunk_size=len(chunk['content']),
                start_position=chunk.get('start', 0),
                end_position=chunk.get('end', len(chunk['content'])),
                page_number=chunk.get('page_number'),
                section_title=chunk.get('section_title', '')
            )
            chunk_objects.append(chunk_obj)
        
        DocumentChunk.objects.bulk_create(chunk_objects)
        
        # Etapa 3: Gerar embeddings
        embedding_service.generate_embeddings_for_document(document)
        
        # Finalizar processamento
        document.status = 'processed'
        document.processed_at = datetime.now()
        document.save()
        
        job.status = 'completed'
        job.completed_at = datetime.now()
        job.result = {
            'chunks_created': len(chunk_objects),
            'markdown_length': len(result['markdown_content']),
            'metadata': result['metadata']
        }
        job.save()
        
        return {
            'success': True,
            'document_id': document.id,
            'chunks_created': len(chunk_objects)
        }
        
    except Exception as e:
        # Atualizar status de erro
        document.status = 'error'
        document.processing_error = str(e)
        document.save()
        
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = datetime.now()
        job.save()
        
        return {
            'success': False,
            'error': str(e),
            'document_id': document.id
        }

@shared_task
def cleanup_old_processed_files():
    """Limpar arquivos processados antigos"""
    try:
        # Implementar lógica de limpeza se necessário
        pass
    except Exception as e:
        return {'success': False, 'error': str(e)}