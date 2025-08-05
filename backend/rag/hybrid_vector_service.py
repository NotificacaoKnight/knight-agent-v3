"""
Hybrid Vector Service - Wrapper para escolher entre pgvector e FAISS
Permite migração gradual e fallback automático
"""

import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class HybridVectorService:
    """
    Serviço híbrido que escolhe entre pgvector e FAISS baseado em configuração.
    Permite migração gradual com fallback automático.
    """
    
    def __init__(self):
        self.use_pgvector = getattr(settings, 'USE_PGVECTOR', False)
        self.enable_fallback = getattr(settings, 'ENABLE_VECTOR_FALLBACK', True)
        self.pgvector_service = None
        self.faiss_service = None
        
        self._initialize_services()
    
    def _initialize_services(self):
        """Inicializa os serviços baseado na configuração"""
        if self.use_pgvector:
            try:
                from .pgvector_service import PgVectorSearchService
                self.pgvector_service = PgVectorSearchService()
                logger.info("PgVector service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize pgvector service: {e}")
                if not self.enable_fallback:
                    raise
                self.use_pgvector = False
        
        # Sempre inicializar FAISS como fallback se habilitado
        if not self.use_pgvector or self.enable_fallback:
            try:
                from .services import VectorSearchService
                self.faiss_service = VectorSearchService()
                logger.info("FAISS service initialized as fallback")
            except Exception as e:
                logger.error(f"Failed to initialize FAISS service: {e}")
                if not self.use_pgvector:
                    raise
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        document_ids: Optional[List[int]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Busca vetorial com fallback automático
        """
        # Tentar pgvector primeiro se configurado
        if self.use_pgvector and self.pgvector_service:
            try:
                results = self.pgvector_service.search(
                    query=query,
                    k=k,
                    document_ids=document_ids,
                    **kwargs
                )
                
                if results:
                    logger.debug(f"PgVector search returned {len(results)} results")
                    return results
                    
            except Exception as e:
                logger.error(f"PgVector search failed: {e}")
                if not self.enable_fallback:
                    raise
        
        # Fallback para FAISS
        if self.faiss_service:
            try:
                logger.debug("Using FAISS fallback for search")
                
                # FAISS tem interface diferente, adaptar parâmetros
                results = self.faiss_service.search(
                    query=query,
                    k=k
                )
                
                # Adaptar formato de resposta se necessário
                if results and isinstance(results, list):
                    # Garantir formato consistente
                    formatted_results = []
                    for result in results:
                        if isinstance(result, dict):
                            # Normalizar campos
                            formatted_result = {
                                'document_id': result.get('document_id'),
                                'chunk_id': result.get('chunk_id'),
                                'chunk_index': result.get('chunk_index'),
                                'content': result.get('content', ''),
                                'score': float(result.get('score', 0.0)),
                                'search_type': 'faiss_fallback'
                            }
                            formatted_results.append(formatted_result)
                    
                    return formatted_results
                
                return results
                
            except Exception as e:
                logger.error(f"FAISS search also failed: {e}")
                raise
        
        # Se chegou aqui, nenhum serviço está disponível
        logger.error("No vector search service available")
        return []
    
    def add_document_embeddings(self, document):
        """
        Adiciona embeddings de documento com suporte a ambos os backends
        """
        success = False
        
        # Tentar pgvector primeiro
        if self.use_pgvector and self.pgvector_service:
            try:
                self.pgvector_service.add_document_embeddings(document)
                success = True
                logger.info(f"Document {document.id} embeddings added to pgvector")
            except Exception as e:
                logger.error(f"Failed to add embeddings to pgvector: {e}")
                if not self.enable_fallback:
                    raise
        
        # Adicionar ao FAISS também se for fallback ou dual-write
        if self.faiss_service and (not success or self.enable_fallback):
            try:
                self.faiss_service.add_document_embeddings(document.id)
                logger.info(f"Document {document.id} embeddings added to FAISS")
            except Exception as e:
                logger.error(f"Failed to add embeddings to FAISS: {e}")
                if not success:
                    raise
    
    def remove_document_embeddings(self, document_id: int):
        """
        Remove embeddings de documento de ambos os backends
        """
        removed = False
        
        # Remover do pgvector
        if self.use_pgvector and self.pgvector_service:
            try:
                count = self.pgvector_service.remove_document_embeddings(document_id)
                logger.info(f"Removed {count} embeddings from pgvector for document {document_id}")
                removed = True
            except Exception as e:
                logger.error(f"Failed to remove from pgvector: {e}")
        
        # Remover do FAISS também
        if self.faiss_service:
            try:
                self.faiss_service.remove_document_embeddings(document_id)
                logger.info(f"Removed embeddings from FAISS for document {document_id}")
                removed = True
            except Exception as e:
                logger.error(f"Failed to remove from FAISS: {e}")
        
        if not removed:
            logger.warning(f"No embeddings removed for document {document_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do serviço ativo
        """
        stats = {
            'active_backend': 'pgvector' if self.use_pgvector else 'faiss',
            'fallback_enabled': self.enable_fallback
        }
        
        if self.use_pgvector and self.pgvector_service:
            try:
                pgvector_stats = self.pgvector_service.get_stats()
                stats['pgvector'] = pgvector_stats
            except Exception as e:
                stats['pgvector_error'] = str(e)
        
        if self.faiss_service:
            try:
                # FAISS não tem get_stats por padrão, mas podemos pegar info básica
                if hasattr(self.faiss_service, 'vector_store') and self.faiss_service.vector_store:
                    stats['faiss'] = {
                        'index_size': self.faiss_service.vector_store.ntotal,
                        'dimension': self.faiss_service.vector_store.d if hasattr(self.faiss_service.vector_store, 'd') else None
                    }
            except Exception as e:
                stats['faiss_error'] = str(e)
        
        return stats
    
    def migrate_to_pgvector(self, batch_size: int = 1000):
        """
        Migra dados do FAISS para pgvector
        """
        if not self.pgvector_service:
            raise ValueError("PgVector service not initialized")
        
        try:
            migrated = self.pgvector_service.migrate_from_faiss(batch_size)
            logger.info(f"Successfully migrated {migrated} chunks to pgvector")
            return migrated
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise