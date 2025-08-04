"""
Comando para testar o fluxo de exclusão de documentos
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from documents.models import Document, DocumentChunk
from rag.services import HybridSearchService
from rag.agentic_rag_service import AgenticRAGServiceSync
from rag.cache_manager import RAGCacheManager
import time


class Command(BaseCommand):
    help = 'Testa o fluxo de exclusão de documentos e verifica se o conteúdo é removido da RAG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=int,
            help='ID do documento para testar exclusão'
        )
        parser.add_argument(
            '--test-query',
            type=str,
            default='',
            help='Query para testar se o conteúdo ainda está acessível'
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        test_query = options.get('test_query')
        
        if not document_id:
            # Listar documentos disponíveis
            documents = Document.objects.filter(status='processed')
            if not documents.exists():
                self.stdout.write(self.style.ERROR('Nenhum documento processado encontrado'))
                return
            
            self.stdout.write(self.style.WARNING('Documentos disponíveis:'))
            for doc in documents[:10]:
                chunks_count = doc.chunks.count()
                self.stdout.write(f"  ID: {doc.id} - {doc.title} ({chunks_count} chunks)")
            
            self.stdout.write(self.style.WARNING('\nUse --document-id para especificar qual documento testar'))
            return
        
        # Buscar documento
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Documento {document_id} não encontrado'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n=== Testando exclusão do documento: {document.title} ===\n'))
        
        # Se não foi fornecida uma query, pegar um trecho do primeiro chunk
        if not test_query:
            first_chunk = document.chunks.first()
            if first_chunk:
                # Pegar primeiras 50 palavras do chunk
                words = first_chunk.content.split()[:50]
                test_query = ' '.join(words[:10])  # Usar primeiras 10 palavras como query
                self.stdout.write(f'Query de teste automática: "{test_query}"\n')
        
        # 1. Testar busca ANTES da exclusão
        self.stdout.write(self.style.WARNING('1. Testando busca ANTES da exclusão...'))
        
        hybrid_service = HybridSearchService()
        agentic_service = AgenticRAGServiceSync()
        
        # Busca híbrida tradicional
        results_before_hybrid = hybrid_service.search(test_query, k=5)
        
        # Tratar caso onde search retorna tuple (results, metadata)
        if isinstance(results_before_hybrid, tuple):
            results_before_hybrid = results_before_hybrid[0]
        
        # Converter para formato esperado se necessário
        if isinstance(results_before_hybrid, list):
            results_before_hybrid = {'results': results_before_hybrid}
        
        found_before_hybrid = any(
            r.get('document_id') == document_id 
            for r in results_before_hybrid.get('results', [])
        )
        
        # Busca agentic
        results_before_agentic = agentic_service.search(test_query, k=5)
        found_before_agentic = False
        if 'error' not in results_before_agentic:
            found_before_agentic = any(
                r.get('document_id') == document_id 
                for r in results_before_agentic.get('results', [])
            )
        
        self.stdout.write(f'  Híbrida: Documento {"ENCONTRADO" if found_before_hybrid else "NÃO encontrado"}')
        self.stdout.write(f'  Agentic: Documento {"ENCONTRADO" if found_before_agentic else "NÃO encontrado"}')
        
        if not found_before_hybrid and not found_before_agentic:
            self.stdout.write(self.style.WARNING('\nDocumento não foi encontrado antes da exclusão. Tente uma query diferente.'))
            return
        
        # 2. Excluir documento
        self.stdout.write(self.style.WARNING('\n2. Excluindo documento...'))
        chunks_count = document.chunks.count()
        
        with transaction.atomic():
            document.delete()
        
        self.stdout.write(self.style.SUCCESS(f'  Documento excluído ({chunks_count} chunks removidos)'))
        
        # 3. Aguardar um pouco para garantir que signals foram processados
        self.stdout.write(self.style.WARNING('\n3. Aguardando processamento dos signals...'))
        time.sleep(2)
        
        # 4. Verificar status dos caches
        self.stdout.write(self.style.WARNING('\n4. Verificando status dos caches...'))
        needs_rebuild = cache.get('indices_need_rebuild')
        self.stdout.write(f'  Flag indices_need_rebuild: {needs_rebuild}')
        
        # 5. Testar busca DEPOIS da exclusão
        self.stdout.write(self.style.WARNING('\n5. Testando busca DEPOIS da exclusão...'))
        
        # Recriar serviços para forçar reload
        hybrid_service = HybridSearchService()
        agentic_service = AgenticRAGServiceSync()
        
        # Busca híbrida tradicional
        results_after_hybrid = hybrid_service.search(test_query, k=5)
        
        # Tratar caso onde search retorna tuple (results, metadata)
        if isinstance(results_after_hybrid, tuple):
            results_after_hybrid = results_after_hybrid[0]
        
        # Converter para formato esperado se necessário
        if isinstance(results_after_hybrid, list):
            results_after_hybrid = {'results': results_after_hybrid}
        
        found_after_hybrid = any(
            r.get('document_id') == document_id 
            for r in results_after_hybrid.get('results', [])
        )
        
        # Busca agentic
        results_after_agentic = agentic_service.search(test_query, k=5)
        found_after_agentic = False
        if 'error' not in results_after_agentic:
            found_after_agentic = any(
                r.get('document_id') == document_id 
                for r in results_after_agentic.get('results', [])
            )
        
        self.stdout.write(f'  Híbrida: Documento {"AINDA ENCONTRADO ❌" if found_after_hybrid else "removido com sucesso ✓"}')
        self.stdout.write(f'  Agentic: Documento {"AINDA ENCONTRADO ❌" if found_after_agentic else "removido com sucesso ✓"}')
        
        # 6. Resultado final
        self.stdout.write(self.style.WARNING('\n=== RESULTADO DO TESTE ==='))
        
        if not found_after_hybrid and not found_after_agentic:
            self.stdout.write(self.style.SUCCESS('✓ SUCESSO: Documento foi completamente removido do sistema RAG'))
        else:
            self.stdout.write(self.style.ERROR('✗ FALHA: Documento ainda está acessível após exclusão'))
            
            if found_after_hybrid:
                self.stdout.write(self.style.ERROR('  - Problema no serviço híbrido'))
            if found_after_agentic:
                self.stdout.write(self.style.ERROR('  - Problema no serviço agentic'))
            
            self.stdout.write(self.style.WARNING('\nDica: Verifique se os caches estão sendo invalidados corretamente'))