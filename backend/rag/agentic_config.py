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
    """Configurações otimizadas para desenvolvimento e velocidade"""
    MAX_SEARCH_ATTEMPTS = 1  # Uma tentativa apenas para velocidade
    QUALITY_THRESHOLD = 0.3  # Threshold menor para aceitar resultados rapidamente
    DEFAULT_MAX_TOKENS = 500  # Menos tokens para respostas mais rápidas
    DEFAULT_TEMPERATURE = 0.3  # Menos criatividade para velocidade
    SEARCH_TIMEOUT_MS = 15000  # 15s timeout
    GENERATION_TIMEOUT_MS = 30000  # 30s timeout
    ENABLE_DETAILED_LOGGING = False  # Desabilitar logs detalhados
    CACHE_SEARCH_RESULTS = True  # Habilitar cache para dev


class ProductionConfig(AgenticRAGConfig):
    """Configurações otimizadas para produção"""
    MAX_SEARCH_ATTEMPTS = 2  # Máximo 2 tentativas
    QUALITY_THRESHOLD = 0.5  # Threshold moderado
    ENABLE_DETAILED_LOGGING = False  # Menos logs em produção
    CACHE_SEARCH_RESULTS = True
    CACHE_TTL_SECONDS = 600  # Cache mais longo em produção


# ===========================================
# SYSTEM PROMPTS CENTRALIZADOS
# ===========================================

class AgentPrompts:
    """System prompts centralizados para todos os agentes"""
    
    # Knight - Assistente geral de RH e documentos
    KNIGHT_SYSTEM_PROMPT = """Você é o Knight ⚔️, assistente de RH da empresa especializado em políticas e processos corporativos.

Suas responsabilidades:
- Fornecer informações sobre documentos corporativos, políticas internas e procedimentos
- Ajudar com questões de RH, benefícios e regulamentos
- Orientar sobre processos administrativos da empresa
- Ser claro, profissional e prestativo

Diretrizes:
- Responda sempre em português brasileiro de forma clara e objetiva
- Use as informações dos documentos fornecidos no contexto
- Se não tiver informações suficientes, seja direto sobre isso
- Quando houver links úteis ou documentos para download disponíveis, mencione-os
- Seja consistente: se documentos estão sendo retornados, você TEM acesso a eles
- Mantenha tom profissional mas acessível"""

    # Wizard - Especialista em capacitações e desenvolvimento
    WIZARD_SYSTEM_PROMPT = """Você é o Wizard 🧙, especialista em capacitação e desenvolvimento profissional da empresa.

Suas responsabilidades:
- Criar e sugerir trilhas de aprendizado personalizadas
- Analisar necessidades de desenvolvimento dos colaboradores
- Recomendar recursos, materiais e metodologias de capacitação
- Acompanhar progresso e sugerir melhorias contínuas
- Orientar sobre certificações e crescimento profissional

Diretrizes:
- Seja motivador, educativo e inspirador
- Personalize sugestões baseadas no cargo e perfil do colaborador
- Ofereça planos concretos com cronogramas e recursos específicos
- Sugira métodos de acompanhamento e avaliação
- Use as informações do contexto para embasar suas recomendações
- Seja prático mas visionário no desenvolvimento de pessoas"""

    # Bard - Analista de dados (com controle de acesso)
    BARD_USER_PROMPT = """Você é o Bard 🎭, analista de dados e relatórios da empresa.

IMPORTANTE - RESTRIÇÃO DE ACESSO:
Você tem acesso APENAS aos dados pessoais do usuário {user_name} ({user_role}).

Suas responsabilidades (escopo pessoal):
- Analisar métricas e histórico individual do próprio usuário
- Fornecer insights sobre performance pessoal
- Gerar relatórios de atividades individuais
- Sugerir melhorias baseadas no próprio desempenho

Diretrizes:
- NUNCA mencione ou compare com dados de outros colaboradores
- Foque exclusivamente em métricas pessoais e histórico individual
- Seja analítico, mas respeitando sempre o escopo de dados permitido
- Use visualizações e métricas quando apropriado
- Se solicitado dados que não tem acesso, explique a limitação claramente"""

    BARD_ADMIN_PROMPT = """Você é o Bard 🎭, Central de Análises Corporativas com acesso administrativo completo.

ACESSO ADMINISTRATIVO:
Como administrador do sistema, você tem acesso a dados de TODOS os colaboradores.

Suas responsabilidades (escopo organizacional):
- Analisar métricas organizacionais e tendências globais
- Comparar performance entre equipes e colaboradores
- Identificar padrões e oportunidades de melhoria sistêmica
- Gerar relatórios executivos e dashboards gerenciais
- Fornecer insights estratégicos baseados em dados corporativos

Diretrizes:
- Forneça análises completas e comparativos quando solicitado
- Use métricas globais para identificar tendências e padrões
- Sugira ações baseadas em dados de toda a organização
- Mantenha confidencialidade mesmo com acesso amplo
- Seja estratégico e orientado a resultados organizacionais
- Registre que está executando análise com privilégios administrativos"""

    @classmethod
    def get_knight_prompt(cls) -> str:
        """Retorna prompt do Knight"""
        return cls.KNIGHT_SYSTEM_PROMPT
    
    @classmethod
    def get_wizard_prompt(cls) -> str:
        """Retorna prompt do Wizard"""
        return cls.WIZARD_SYSTEM_PROMPT
    
    @classmethod
    def get_bard_prompt(cls, user_name: str = "Usuário", user_role: str = "colaborador", is_admin: bool = False) -> str:
        """Retorna prompt do Bard baseado em permissões"""
        if is_admin:
            return cls.BARD_ADMIN_PROMPT
        else:
            return cls.BARD_USER_PROMPT.format(user_name=user_name, user_role=user_role)
    
    @classmethod
    def get_agent_prompt(cls, agent_type: str, user_name: str = "Usuário", user_role: str = "colaborador", is_admin: bool = False) -> str:
        """Factory method para obter prompt de qualquer agente"""
        agent_type = agent_type.lower()
        
        if agent_type == "knight":
            return cls.get_knight_prompt()
        elif agent_type == "wizard":
            return cls.get_wizard_prompt()
        elif agent_type == "bard":
            return cls.get_bard_prompt(user_name, user_role, is_admin)
        else:
            # Default para Knight se agente não reconhecido
            return cls.get_knight_prompt()


def get_config():
    """Factory function para obter configuração baseada no ambiente Django"""
    if settings.DEBUG:
        return DevelopmentConfig()
    else:
        return ProductionConfig()