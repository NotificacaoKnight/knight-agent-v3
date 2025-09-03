"""
Cache global thread-safe para modelos SentenceTransformer
Evita múltiplas cargas simultâneas e resolve problemas de race condition
"""
import threading
import logging
from typing import Dict, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Lock global para proteger carregamento de modelos
_model_lock = threading.Lock()

# Cache global de modelos carregados
_model_cache: Dict[str, Optional[SentenceTransformer]] = {}

def get_cached_model(model_name: str, device: str = 'cpu') -> Optional[SentenceTransformer]:
    """
    Obtém modelo SentenceTransformer do cache global thread-safe
    
    Args:
        model_name: Nome do modelo (ex: 'BAAI/bge-m3')
        device: Device para carregar o modelo ('cpu' ou 'cuda')
        
    Returns:
        SentenceTransformer carregado ou None se falhou
    """
    with _model_lock:
        # Se modelo já está no cache, retornar
        if model_name in _model_cache:
            cached_model = _model_cache[model_name]
            if cached_model is not None:
                logger.info(f"Modelo {model_name} obtido do cache")
                return cached_model
            else:
                logger.warning(f"Modelo {model_name} falhou anteriormente, retornando None")
                return None
        
        # Carregar modelo pela primeira vez
        try:
            logger.info(f"Carregando modelo {model_name} pela primeira vez...")
            model = SentenceTransformer(model_name, device=device)
            _model_cache[model_name] = model
            logger.info(f"Modelo {model_name} carregado com sucesso e armazenado em cache")
            return model
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {model_name}: {e}")
            # Armazenar None para evitar tentativas repetidas
            _model_cache[model_name] = None
            return None

def clear_model_cache():
    """Limpa cache de modelos - útil para testes"""
    global _model_cache
    with _model_lock:
        _model_cache.clear()
        logger.info("Cache de modelos limpo")

def get_cache_stats() -> Dict[str, int]:
    """Retorna estatísticas do cache"""
    with _model_lock:
        total_models = len(_model_cache)
        loaded_models = sum(1 for model in _model_cache.values() if model is not None)
        failed_models = total_models - loaded_models
        
        return {
            'total_models': total_models,
            'loaded_models': loaded_models,
            'failed_models': failed_models
        }