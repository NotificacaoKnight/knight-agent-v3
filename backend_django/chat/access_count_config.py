"""
Configuração do sistema de contagem de acesso inteligente baseado em relevância
"""
import os
from typing import Literal

# Estratégias disponíveis
AccessCountStrategy = Literal['top_n', 'single_best', 'threshold_only']

class AccessCountConfig:
    """Configuração centralizada para contagem de acesso inteligente"""
    
    # Configurações padrão (podem ser sobrescritas via environment)
    DEFAULT_MIN_SCORE = 0.6
    DEFAULT_STRATEGY = 'single_best'
    DEFAULT_MAX_DOCS = 3
    
    @staticmethod
    def get_min_score() -> float:
        """Threshold mínimo de relevância para incrementar access_count"""
        return float(os.getenv('DOCUMENT_ACCESS_MIN_SCORE', AccessCountConfig.DEFAULT_MIN_SCORE))
    
    @staticmethod
    def get_strategy() -> AccessCountStrategy:
        """Estratégia de seleção de documentos relevantes"""
        strategy = os.getenv('DOCUMENT_ACCESS_STRATEGY', AccessCountConfig.DEFAULT_STRATEGY)
        if strategy not in ['top_n', 'single_best', 'threshold_only']:
            return AccessCountConfig.DEFAULT_STRATEGY
        return strategy
    
    @staticmethod 
    def get_max_docs() -> int:
        """Máximo de documentos únicos a incrementar (usado em top_n)"""
        return int(os.getenv('DOCUMENT_ACCESS_MAX_DOCS', AccessCountConfig.DEFAULT_MAX_DOCS))
    
    @staticmethod
    def get_config_summary() -> dict:
        """Retorna resumo da configuração atual"""
        return {
            'min_score': AccessCountConfig.get_min_score(),
            'strategy': AccessCountConfig.get_strategy(), 
            'max_docs': AccessCountConfig.get_max_docs(),
            'description': AccessCountConfig.get_strategy_description()
        }
    
    @staticmethod
    def get_strategy_description() -> str:
        """Descrição da estratégia atual"""
        strategy = AccessCountConfig.get_strategy()
        descriptions = {
            'top_n': f'Incrementa até {AccessCountConfig.get_max_docs()} documentos mais relevantes com score ≥ {AccessCountConfig.get_min_score()}',
            'single_best': f'Incrementa apenas o documento mais relevante com score ≥ {AccessCountConfig.get_min_score()}',
            'threshold_only': f'Incrementa todos os documentos únicos com score ≥ {AccessCountConfig.get_min_score()}'
        }
        return descriptions.get(strategy, 'Estratégia desconhecida')