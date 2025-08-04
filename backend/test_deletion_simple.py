#!/usr/bin/env python
"""
Script simples para testar exclusão de documentos
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'knight_backend.settings')
django.setup()

from documents.models import Document
from rag.services import VectorSearchService, BM25SearchService
from rag.cache_manager import RAGCacheManager
from django.core.cache import cache
import time

def test_deletion():
    print("\n=== TESTE DE EXCLUSÃO DE DOCUMENTOS ===\n")
    
    # 1. Listar documentos
    docs = Document.objects.filter(status='processed')
    if not docs:
        print("❌ Nenhum documento processado encontrado")
        return
    
    doc = docs.first()
    doc_id = doc.id
    print(f"📄 Testando com documento: {doc.title} (ID: {doc_id})")
    
    # 2. Pegar um trecho do primeiro chunk como query de teste
    first_chunk = doc.chunks.first()
    if not first_chunk:
        print("❌ Documento não tem chunks")
        return
    
    test_query = ' '.join(first_chunk.content.split()[:10])
    print(f"🔍 Query de teste: '{test_query}'")
    
    # 3. Testar busca ANTES da exclusão
    print("\n1️⃣ Testando busca ANTES da exclusão...")
    
    vector_service = VectorSearchService()
    bm25_service = BM25SearchService()
    
    # Busca vetorial
    vector_results = vector_service.search(test_query, k=5)
    found_vector_before = any(r['document_id'] == doc_id for r in vector_results)
    
    # Busca BM25
    bm25_results = bm25_service.search(test_query, k=5)
    found_bm25_before = any(r['document_id'] == doc_id for r in bm25_results)
    
    print(f"  Vector: {'✓ Encontrado' if found_vector_before else '✗ Não encontrado'}")
    print(f"  BM25: {'✓ Encontrado' if found_bm25_before else '✗ Não encontrado'}")
    
    if not found_vector_before and not found_bm25_before:
        print("\n⚠️ Documento não foi encontrado antes da exclusão. Abortando teste.")
        return
    
    # 4. Excluir documento
    print(f"\n2️⃣ Excluindo documento ID {doc_id}...")
    doc.delete()
    print("  ✓ Documento excluído do banco de dados")
    
    # 5. Aguardar processamento
    print("\n3️⃣ Aguardando 2 segundos...")
    time.sleep(2)
    
    # 6. Verificar caches
    print("\n4️⃣ Status dos caches:")
    needs_rebuild = cache.get('indices_need_rebuild')
    print(f"  indices_need_rebuild: {needs_rebuild}")
    
    # 7. Recriar serviços (força reload)
    print("\n5️⃣ Testando busca DEPOIS da exclusão...")
    
    vector_service = VectorSearchService()
    bm25_service = BM25SearchService()
    
    # Busca vetorial
    vector_results = vector_service.search(test_query, k=5)
    found_vector_after = any(r['document_id'] == doc_id for r in vector_results)
    
    # Busca BM25
    bm25_results = bm25_service.search(test_query, k=5)
    found_bm25_after = any(r['document_id'] == doc_id for r in bm25_results)
    
    print(f"  Vector: {'❌ AINDA ENCONTRADO' if found_vector_after else '✓ Removido'}")
    print(f"  BM25: {'❌ AINDA ENCONTRADO' if found_bm25_after else '✓ Removido'}")
    
    # 8. Resultado final
    print("\n" + "="*50)
    if not found_vector_after and not found_bm25_after:
        print("✅ SUCESSO: Documento foi completamente removido!")
    else:
        print("❌ FALHA: Documento ainda está acessível após exclusão")
        if found_vector_after:
            print("  - Problema no índice vetorial (FAISS)")
        if found_bm25_after:
            print("  - Problema no índice BM25")

if __name__ == "__main__":
    test_deletion()