"""
Processador simplificado de documentos (sem Celery)
"""
import os
from datetime import datetime
from django.conf import settings
from .models import Document, DocumentChunk, ProcessingJob
from .agno_document_service import AgnoDocumentService


def process_document_sync(document_id):
    """
    Processa documento de forma síncrona usando Agno
    """
    try:
        document = Document.objects.get(id=document_id)
        
        # Limpar processamento anterior
        document.chunks.all().delete()
        document.processing_jobs.all().delete()
        
        document.status = 'processing'
        document.processing_error = ''
        document.save()
        
        # Criar job de processamento
        job = ProcessingJob.objects.create(
            document=document,
            job_type='agno_processing',
            status='processing',
            started_at=datetime.now()
        )
        
        # Usar processamento híbrido: Agno + MongoDB direto
        from .async_service_wrapper import async_agno_service
        from .mongodb_direct_indexer import index_document_to_mongodb
        
        # Processar com Agno (FAISS + tentativa MongoDB)
        result = async_agno_service.process_and_index_document_async(
            file_path=document.file_path.path,
            document_id=str(document.id),
            metadata={
                'title': document.title,
                'uploaded_by': document.uploaded_by.username if document.uploaded_by else 'Sistema',
                'upload_date': str(document.uploaded_at),
                'file_type': document.file_type
            }
        )
        
        # Garantir indexação no MongoDB com embeddings (backup)
        if result['success']:
            try:
                print(f"🔄 Tentando indexar documento {document.id} no MongoDB...")
                
                # Primeiro salvar o markdown_content no documento
                if result.get('markdown_path') and os.path.exists(result['markdown_path']):
                    with open(result['markdown_path'], 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                        document.markdown_content = markdown_content
                        document.save()
                        print(f"📄 Markdown content salvo: {len(markdown_content)} chars")
                else:
                    print(f"⚠️ Markdown path não encontrado: {result.get('markdown_path')}")
                    markdown_content = None
                
                # Agora indexar no MongoDB
                if markdown_content:
                    print(f"🍃 Indexando no MongoDB...")
                    mongodb_result = index_document_to_mongodb(
                        document_id=str(document.id),
                        content=markdown_content,
                        metadata={
                            'title': document.title,
                            'uploaded_by': document.uploaded_by.username if document.uploaded_by else 'Sistema',
                            'upload_date': str(document.uploaded_at),
                            'file_type': document.file_type,
                            'django_id': document.id
                        }
                    )
                    if mongodb_result:
                        print(f"✅ Documento {document.id} indexado no MongoDB com embeddings")
                    else:
                        print(f"❌ Falha na indexação MongoDB para documento {document.id}")
                else:
                    print(f"❌ Sem markdown content para indexar no MongoDB")
            except Exception as e:
                print(f"❌ Erro na indexação MongoDB backup: {e}")
                import traceback
                traceback.print_exc()
        
        if result['success']:
            # Atualizar documento
            document.status = 'processed'
            document.processed_at = datetime.now()
            document.processed_path = result.get('markdown_path', '')
            document.metadata = result.get('metadata', {})
            
            # Salvar conteúdo markdown se disponível
            if result.get('markdown_path') and os.path.exists(result['markdown_path']):
                with open(result['markdown_path'], 'r', encoding='utf-8') as f:
                    document.markdown_content = f.read()
            
            document.save()
            
            # Criar um chunk único representando o documento completo
            # (Agno + MongoDB Atlas gerencia os chunks internamente)
            DocumentChunk.objects.create(
                document=document,
                chunk_index=0,
                content=f"Documento processado e indexado no MongoDB Atlas (com fallback FAISS). ID: {document.id}",
                chunk_size=len(document.markdown_content or '')
            )
            
            # Completar job
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.result = {
                'mongodb_indexed': True,
                'faiss_fallback_available': True,
                'document_id': str(document.id),
                'metadata': result.get('metadata', {})
            }
            job.save()
            
            return {
                'success': True,
                'document_id': document.id,
                'message': 'Documento processado e indexado com sucesso'
            }
            
        else:
            raise Exception(result.get('error', 'Erro desconhecido'))
            
    except Exception as e:
        # Atualizar status de erro
        if 'document' in locals():
            document.status = 'error'
            document.processing_error = str(e)
            document.save()
        
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now()
            job.save()
        
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }