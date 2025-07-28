"""
Configurações para o sistema RAG Agentic
Centralizando parâmetros configuráveis para evitar hardcoded values
"""
from django.conf import settings


class AgenticRAGConfig:
    """Configurações centralizadas para RAG Agentic"""
    
    # Limites de busca e tentativas
    MAX_SEARCH_ATTEMPTS = getattr(settings, 'AGENTIC_RAG_MAX_SEARCH_ATTEMPTS', 3)
    QUALITY_THRESHOLD = getattr(settings, 'AGENTIC_RAG_QUALITY_THRESHOLD', 0.6)
    MAX_CONTEXT_LENGTH = getattr(settings, 'AGENTIC_RAG_MAX_CONTEXT_LENGTH', 8000)
    
    # Pesos para busca híbrida
    DEFAULT_SEMANTIC_WEIGHT = getattr(settings, 'AGENTIC_RAG_SEMANTIC_WEIGHT', 0.7)
    DEFAULT_BM25_WEIGHT = getattr(settings, 'AGENTIC_RAG_BM25_WEIGHT', 0.3)
    
    # Configurações de geração
    DEFAULT_MAX_TOKENS = getattr(settings, 'AGENTIC_RAG_MAX_TOKENS', 1000)
    DEFAULT_TEMPERATURE = getattr(settings, 'AGENTIC_RAG_TEMPERATURE', 0.7)
    
    # Timeouts e performance
    SEARCH_TIMEOUT_MS = getattr(settings, 'AGENTIC_RAG_SEARCH_TIMEOUT_MS', 30000)
    GENERATION_TIMEOUT_MS = getattr(settings, 'AGENTIC_RAG_GENERATION_TIMEOUT_MS', 60000)
    
    # Qualidade e avaliação
    MIN_RESULT_SCORE = getattr(settings, 'AGENTIC_RAG_MIN_RESULT_SCORE', 0.1)
    RESPONSE_MIN_LENGTH = getattr(settings, 'AGENTIC_RAG_RESPONSE_MIN_LENGTH', 10)
    
    # Weights para quality evaluation
    QUALITY_WEIGHTS = {
        'avg_score': getattr(settings, 'AGENTIC_RAG_QUALITY_AVG_SCORE_WEIGHT', 0.4),
        'result_count': getattr(settings, 'AGENTIC_RAG_QUALITY_RESULT_COUNT_WEIGHT', 0.3),
        'relevance': getattr(settings, 'AGENTIC_RAG_QUALITY_RELEVANCE_WEIGHT', 0.3)
    }
    
    RESPONSE_QUALITY_WEIGHTS = {
        'length': getattr(settings, 'AGENTIC_RAG_RESPONSE_LENGTH_WEIGHT', 0.3),
        'context_usage': getattr(settings, 'AGENTIC_RAG_RESPONSE_CONTEXT_WEIGHT', 0.3),
        'relevance': getattr(settings, 'AGENTIC_RAG_RESPONSE_RELEVANCE_WEIGHT', 0.4)
    }
    
    # Logging e monitoring
    ENABLE_DETAILED_LOGGING = getattr(settings, 'AGENTIC_RAG_DETAILED_LOGGING', True)
    LOG_LEVEL = getattr(settings, 'AGENTIC_RAG_LOG_LEVEL', 'INFO')
    
    # Cache settings
    CACHE_SEARCH_RESULTS = getattr(settings, 'AGENTIC_RAG_CACHE_SEARCH', True)
    CACHE_TTL_SECONDS = getattr(settings, 'AGENTIC_RAG_CACHE_TTL', 300)  # 5 minutes
    
    @classmethod
    def get_search_config(cls) -> dict:
        """Retorna configuração para busca"""
        return {
            'max_attempts': cls.MAX_SEARCH_ATTEMPTS,
            'quality_threshold': cls.QUALITY_THRESHOLD,
            'semantic_weight': cls.DEFAULT_SEMANTIC_WEIGHT,
            'bm25_weight': cls.DEFAULT_BM25_WEIGHT,
            'timeout_ms': cls.SEARCH_TIMEOUT_MS
        }
    
    @classmethod
    def get_generation_config(cls) -> dict:
        """Retorna configuração para geração"""
        return {
            'max_tokens': cls.DEFAULT_MAX_TOKENS,
            'temperature': cls.DEFAULT_TEMPERATURE,
            'timeout_ms': cls.GENERATION_TIMEOUT_MS,
            'max_context_length': cls.MAX_CONTEXT_LENGTH
        }
    
    @classmethod
    def get_quality_config(cls) -> dict:
        """Retorna configuração para avaliação de qualidade"""
        return {
            'threshold': cls.QUALITY_THRESHOLD,
            'min_result_score': cls.MIN_RESULT_SCORE,
            'response_min_length': cls.RESPONSE_MIN_LENGTH,
            'quality_weights': cls.QUALITY_WEIGHTS,
            'response_quality_weights': cls.RESPONSE_QUALITY_WEIGHTS
        }


# Configurações específicas para diferentes contextos
class DevelopmentConfig(AgenticRAGConfig):
    """Configurações otimizadas para desenvolvimento"""
    MAX_SEARCH_ATTEMPTS = 2  # Menos tentativas para desenvolvimento mais rápido
    ENABLE_DETAILED_LOGGING = True
    CACHE_SEARCH_RESULTS = False  # Desabilitar cache em dev


class ProductionConfig(AgenticRAGConfig):
    """Configurações otimizadas para produção"""
    MAX_SEARCH_ATTEMPTS = 3
    ENABLE_DETAILED_LOGGING = False  # Menos logs em produção
    CACHE_SEARCH_RESULTS = True
    CACHE_TTL_SECONDS = 600  # Cache mais longo em produção


def get_config():
    """Factory function para obter configuração baseada no ambiente Django"""
    if settings.DEBUG:
        return DevelopmentConfig()
    else:
        return ProductionConfig()