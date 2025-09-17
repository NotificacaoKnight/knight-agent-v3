"""
Gerenciador centralizado de cache para o sistema RAG
"""

from django.core.cache import cache
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class RAGCacheManager:
    """Gerencia todos os caches relacionados ao sistema RAG"""
    
    # Padrões de cache keys
    CACHE_PATTERNS = {
        'bm25': ['bm25_index', 'bm25_*'],
        'vector': ['vector_store_*', 'faiss_*'],
        'embeddings': ['embedding_*'],
        'agentic': ['agentic_*'],
        'search': ['search_*', 'hybrid_search_*'],
    }
    
    @classmethod
    def clear_all_caches(cls):
        """Limpa todos os caches do sistema RAG"""
        try:
            # Limpar caches específicos
            for category, patterns in cls.CACHE_PATTERNS.items():
                for pattern in patterns:
                    cls._clear_cache_pattern(pattern)
            
            logger.info("Todos os caches do RAG foram limpos")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar caches: {e}")
            return False
    
    @classmethod
    def clear_document_caches(cls, document_id: int):
        """Limpa caches relacionados a um documento específico"""
        try:
            # Limpar caches específicos do documento
            cache_keys = [
                f"document_{document_id}_*",
                f"chunks_{document_id}_*",
                f"embedding_doc_{document_id}_*",
            ]
            
            for key_pattern in cache_keys:
                cls._clear_cache_pattern(key_pattern)
            
            # Invalidar caches de índices que podem conter o documento
            cls.invalidate_search_indices()
            
            logger.info(f"Caches do documento {document_id} foram limpos")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar caches do documento {document_id}: {e}")
            return False
    
    @classmethod
    def invalidate_search_indices(cls):
        """Invalida todos os índices de busca (BM25, FAISS, etc)"""
        try:
            # Limpar índices BM25
            cache.delete('bm25_index')
            cache.delete('bm25_last_update')
            
            # Limpar mapeamentos de vector store
            cache.delete('vector_store_chunk_mapping')
            cache.delete('faiss_index_loaded')
            
            # Limpar caches de busca híbrida
            cls._clear_cache_pattern('hybrid_search_*')
            cls._clear_cache_pattern('search_results_*')
            
            # Forçar reconstrução dos índices na próxima busca
            cache.set('indices_need_rebuild', True, 3600)
            
            logger.info("Índices de busca invalidados")
            return True
        except Exception as e:
            logger.error(f"Erro ao invalidar índices: {e}")
            return False
    
    @classmethod
    def _clear_cache_pattern(cls, pattern: str):
        """Limpa caches que correspondem ao padrão"""
        try:
            # Django cache não suporta wildcards nativamente
            # Mas podemos usar delete_many se disponível
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(pattern)
            elif hasattr(cache, 'delete_many'):
                # Para backends que suportam delete_many
                keys = cache.keys(pattern)
                if keys:
                    cache.delete_many(keys)
            else:
                # Fallback: deletar keys conhecidas
                if '*' not in pattern:
                    cache.delete(pattern)
        except Exception as e:
            logger.warning(f"Não foi possível limpar cache pattern {pattern}: {e}")
    
    @classmethod
    def notify_index_update(cls, update_type: str = 'general'):
        """Notifica que houve atualização nos índices"""
        try:
            cache.set('last_index_update', {
                'type': update_type,
                'timestamp': cls._get_timestamp()
            }, 3600)
            
            # Marcar que índices precisam ser reconstruídos
            cache.set('indices_need_rebuild', True, 3600)
            
            logger.info(f"Notificação de atualização de índice: {update_type}")
        except Exception as e:
            logger.error(f"Erro ao notificar atualização: {e}")
    
    @staticmethod
    def _get_timestamp():
        """Retorna timestamp atual"""
        from datetime import datetime
        return datetime.now().isoformat()