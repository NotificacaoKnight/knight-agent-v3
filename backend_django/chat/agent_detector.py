"""
Sistema de Detecção de Agente Apropriado
Determina qual agente (Knight, Wizard, Bard) é mais adequado para responder a query
"""
import re
from typing import Tuple, Optional


class AgentDetector:
    """Detector inteligente de agente apropriado"""
    
    # Padrões para Wizard - Capacitação e Desenvolvimento
    WIZARD_PATTERNS = [
        # Cursos e treinamentos
        r'\b(curso|cursos|capacita[çc][ãa]o|treinamento|treinamentos)\b',
        r'\b(desenvolvimento profissional|certificar-se|certificação)\b',
        r'\b(aprendizado|aprender|habilidades|competências|skill)\b',
        r'\b(mentoria|coaching|orientação profissional)\b',
        r'\b(workshops?|seminários?|palestras?)\b',
        r'\b(carreira|crescimento profissional|trilha de aprendizado)\b',
        r'\b(qualificação|especialização|formação)\b',
        
        # Termos específicos de capacitação
        r'\b(me ensine|me ajude a aprender|quero aprender)\b',
        r'\b(como posso melhorar|como desenvolver)\b',
        r'\b(preciso estudar|preciso me capacitar)\b',
        
        # Liderança e soft skills
        r'\b(liderança|liderar|gestão de pessoas|gerenciar equipe)\b',
        r'\b(comunicação|apresentação|oratória|soft skills)\b',
        r'\b(feedback|avaliação de desempenho|coaching)\b',
        r'\b(team building|trabalho em equipe|colaboração)\b',
        r'\b(negociação|resolução de conflitos|mediação)\b',
        r'\b(inovação|criatividade|pensamento estratégico)\b',
        r'\b(plano de desenvolvimento|pdp|plano de carreira)\b',
    ]
    
    # Padrões para Bard - Análise e Dados
    BARD_PATTERNS = [
        # Análise de dados
        r'\b(análise|analisar|dados|data|métricas|métrica)\b',
        r'\b(relatório|relatórios|dashboard|painel)\b',
        r'\b(gráfico|gráficos|estatística|estatísticas)\b',
        r'\b(indicador|indicadores|kpi|kpis)\b',
        r'\b(tendência|tendências|performance|desempenho)\b',
        
        # Visualização e números
        r'\b(visualização|visualizar|mostrar dados|apresentar dados)\b',
        r'\b(números|percentual|taxa|índice)\b',
        r'\b(comparar|comparação|evolução|histórico)\b',
        r'\b(ranking|classificação|top\s+\d+)\b',
        
        # Específicos de RH analytics
        r'\b(turnover|rotatividade|absenteísmo)\b',
        r'\b(satisfação|engajamento|clima organizacional)\b',
        r'\b(produtividade|eficiência|resultados)\b',
    ]
    
    # Mensagens de transição do Knight
    HANDOFF_MESSAGES = {
        "wizard": [
            "Ótimo! Vou chamar o Wizard para nos ajudar com {reason}. Ele é nosso especialista em desenvolvimento profissional.",
            "Perfeito! O Wizard é quem pode te orientar melhor sobre {reason}. Vou chamá-lo.",
            "Excelente pergunta! Para {reason}, o Wizard é a pessoa certa. Deixa eu chamar ele.",
        ],
        "bard": [
            "Interessante! Vou chamar o Bard para te ajudar com essa {reason}. Ele adora números!",
            "Boa! Para {reason}, o Bard é perfeito. Ele vai criar uma análise incrível para você.",
            "Legal! O Bard é especialista em {reason}. Vou pedir para ele dar uma olhada.",
        ]
    }
    
    @classmethod
    def detect_appropriate_agent(cls, query: str) -> Tuple[str, Optional[str]]:
        """
        Detecta o agente mais apropriado para a query
        
        Returns:
            Tuple[str, Optional[str]]: (agente, razão_para_transição)
        """
        query_lower = query.lower().strip()
        
        # Prioridade para Wizard (capacitação tem prioridade sobre dados)
        if cls._matches_patterns(query_lower, cls.WIZARD_PATTERNS):
            return ("wizard", "capacitação e desenvolvimento")
        
        # Bard para análise de dados
        if cls._matches_patterns(query_lower, cls.BARD_PATTERNS):
            return ("bard", "análise de dados")
        
        # Knight é o default
        return ("knight", None)
    
    @classmethod
    def _matches_patterns(cls, text: str, patterns: list) -> bool:
        """Verifica se o texto matches algum dos padrões"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def generate_handoff_message(cls, target_agent: str, reason: str) -> str:
        """Gera mensagem de transição do Knight para outro agente"""
        import random
        
        if target_agent not in cls.HANDOFF_MESSAGES:
            return f"Vou chamar um especialista para te ajudar com {reason}."
        
        templates = cls.HANDOFF_MESSAGES[target_agent]
        template = random.choice(templates)
        
        return template.format(reason=reason)
    
    @classmethod
    def get_agent_emoji(cls, agent: str) -> str:
        """Retorna emoji identificador do agente"""
        emojis = {
            "knight": "⚔️",
            "wizard": "🧙", 
            "bard": "🎭"
        }
        return emojis.get(agent, "🤖")
    


# Instância global para facilitar uso
agent_detector = AgentDetector()