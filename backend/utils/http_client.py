"""
Cliente HTTP otimizado com connection pooling para uso geral
"""
from typing import Optional, Dict, Any
import logging
from rag.http_pool import http_pool

logger = logging.getLogger(__name__)

class OptimizedHTTPClient:
    """
    Cliente HTTP otimizado para uso em toda a aplicação
    """
    
    @staticmethod
    def post(url: str, **kwargs) -> Any:
        """POST request com pooling"""
        return http_pool.post(url, **kwargs)
    
    @staticmethod
    def get(url: str, **kwargs) -> Any:
        """GET request com pooling"""
        return http_pool.get(url, **kwargs)
    
    @staticmethod
    def request(method: str, url: str, **kwargs) -> Any:
        """Request genérico com pooling"""
        return http_pool.request(method, url, **kwargs)
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Retorna estatísticas do pool"""
        return http_pool.get_stats()

# Exportar cliente global
http_client = OptimizedHTTPClient()