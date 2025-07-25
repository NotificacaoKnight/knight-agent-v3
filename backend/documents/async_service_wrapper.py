"""
Wrapper assíncrono para usar AgnoDocumentService em views Django
Permite usar métodos async em views síncronas
"""
import asyncio
from typing import Dict, List
from .agno_document_service import AgnoDocumentService
import logging

logger = logging.getLogger(__name__)


class AsyncAgnoDocumentService:
    """
    Wrapper que permite usar métodos assíncronos do AgnoDocumentService
    em views Django síncronas, otimizado para múltiplos usuários
    """
    
    def __init__(self):
        self.service = AgnoDocumentService()
        logger.info("🚀 AsyncAgnoDocumentService inicializado para múltiplos usuários")
    
    def process_and_index_document_async(self, file_path: str, document_id: str, metadata: Dict = None) -> Dict:
        """
        Wrapper síncrono para método assíncrono de processamento
        Ideal para múltiplos usuários simultâneos
        """
        try:
            # Executar método assíncrono em loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.service.aprocess_and_index_document(file_path, document_id, metadata)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Erro no processamento assíncrono: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
    def search_documents_async(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Wrapper síncrono para método assíncrono de busca
        Otimizado para resposta rápida com múltiplos usuários
        """
        try:
            # Executar método assíncrono em loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    self.service.asearch_documents(query, limit)
                )
                return results
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Erro na busca assíncrona: {e}")
            return []
    
    # Manter compatibilidade com métodos síncronos
    def process_and_index_document(self, file_path: str, document_id: str, metadata: Dict = None) -> Dict:
        """Método síncrono tradicional (compatibilidade)"""
        return self.service.process_and_index_document(file_path, document_id, metadata)
    
    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """Método síncrono tradicional (compatibilidade)"""
        return self.service.search_documents(query, limit)
    
    def list_documents(self) -> List[Dict]:
        """Lista documentos indexados"""
        return self.service.list_documents()
    
    def get_document_by_id(self, document_id: str) -> Dict:
        """Busca documento por ID"""
        return self.service.get_document_by_id(document_id)
    
    def delete_document(self, document_id: str) -> bool:
        """Remove documento do índice"""
        return self.service.delete_document(document_id)


# Instância global para reutilização
async_agno_service = AsyncAgnoDocumentService()