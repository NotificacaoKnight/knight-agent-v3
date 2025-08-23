"""
Sistema de Comportamento Inteligente para Knight Agent
Refinamento completo do comportamento de resposta com:
- Prompts padronizados e otimizados
- Análise inteligente de contexto
- Personalização baseada no usuário
- Validação de qualidade avançada
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from django.core.cache import cache


class PromptLibrary:
    """Biblioteca central de prompts profissionais"""
    
    # Prompts base por personalidade de agente
    AGENT_PERSONALITIES = {
        "knight": {
            "role": "Assistente Corporativo Senior especializado em RH e políticas internas",
            "style": "cordial, prestativo, orientado a soluções",
            "expertise": "políticas corporativas, benefícios, processos, regulamentações"
        },
        "bard": {
            "role": "Analista de Dados Senior especializado em insights e relatórios",
            "style": "analítico, orientado a dados, estratégico",
            "expertise": "análise de dados, métricas de performance, dashboards, tendências"
        },
        "wizard": {
            "role": "Especialista em Desenvolvimento Humano e Capacitação",
            "style": "inspirador, didático, estratégico",
            "expertise": "trilhas de aprendizado, capacitação profissional, certificações"
        }
    }
    
    @classmethod
    def get_system_prompt(cls, agent_type: str, user_context: Dict[str, Any] = None) -> str:
        """Gera system prompt personalizado por agente"""
        
        personality = cls.AGENT_PERSONALITIES.get(agent_type, cls.AGENT_PERSONALITIES["knight"])
        user_context = user_context or {}
        
        # Contexto do usuário
        user_name = user_context.get('name', 'Colaborador')
        department = user_context.get('department', '')
        role = user_context.get('role', '')
        
        context_info = f"\nUSUÁRIO: {user_name}"
        if department:
            context_info += f"\nDEPARTAMENTO: {department}"
        if role:
            context_info += f"\nCARGO: {role}"
        
        return f"""Você é o {personality['role']}.
{context_info}

PERSONALIDADE E ESTILO:
- Estilo de comunicação: {personality['style']}
- Especialização: {personality['expertise']}

DIRETRIZES COMPORTAMENTAIS:
1. SEMPRE responda em português brasileiro corporativo
2. Use linguagem profissional mas acessível
3. Seja específico e orientado à ação
4. Inclua próximos passos quando relevante
5. Demonstre empatia e compreensão do contexto empresarial
6. Cite fontes quando baseado em documentos específicos
7. Mantenha tom respeitoso e colaborativo

ESTRUTURA DE RESPOSTA:
- Resposta direta à pergunta
- Contexto adicional relevante
- Sugestões de próximos passos (se aplicável)
- Recursos ou contatos relevantes (se aplicável)

EVITE:
- Respostas genéricas ou vagas
- Jargões excessivos
- Promessas que não pode cumprir
- Informações desatualizadas ou imprecisas"""
    
    @classmethod
    def get_analysis_prompt(cls, query: str, context: str) -> str:
        """Prompt para análise detalhada com contexto"""
        
        return f"""Analise esta consulta corporativa e forneça uma resposta completa e útil.

CONSULTA: {query}

CONTEXTO DISPONÍVEL:
{context}

INSTRUÇÕES PARA RESPOSTA:
1. Analise a consulta no contexto corporativo brasileiro
2. Use APENAS as informações do contexto fornecido
3. Se o contexto for insuficiente, seja transparente sobre limitações
4. Estruture a resposta de forma lógica e profissional
5. Inclua exemplos práticos quando possível
6. Sugira próximos passos concretos

Forneça uma resposta completa, precisa e orientada à ação."""
    
    @classmethod
    def get_intent_analysis_prompt(cls, query: str) -> str:
        """Prompt para análise de intenção otimizada"""
        
        return f"""Analise esta consulta corporativa e identifique o agente mais adequado:

CONSULTA: "{query}"

AGENTES DISPONÍVEIS:
🏛️ KNIGHT - Políticas RH, benefícios, processos internos, regulamentações
📊 BARD - Análises de dados, relatórios, métricas, dashboards, insights
🎓 WIZARD - Capacitação, treinamentos, trilhas de aprendizado, certificações

CRITÉRIOS DE DECISÃO:
- KNIGHT: Questões sobre políticas, benefícios, processos, dúvidas administrativas
- BARD: Solicitações de análise, relatórios, dados, métricas, comparações
- WIZARD: Desenvolvimento profissional, cursos, capacitação, onboarding

ANÁLISE CONTEXTUAL:
- Identifique palavras-chave específicas
- Considere o tipo de resposta esperada
- Avalie a complexidade da consulta

Responda APENAS com: KNIGHT, BARD ou WIZARD"""


class IntelligentBehavior:
    """Sistema inteligente de comportamento e resposta"""
    
    def __init__(self):
        self.prompt_lib = PromptLibrary()
        self._context_cache = {}
        self._user_preferences = {}
    
    def analyze_query_intelligence(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Análise inteligente de query com contexto avançado"""
        
        cache_key = f"intelligent_analysis_{hash(query)}_{hash(str(user_context))}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        query_lower = query.lower()
        user_context = user_context or {}
        
        # 1. ANÁLISE DE COMPLEXIDADE AVANÇADA
        complexity_score = self._calculate_complexity_score(query)
        
        # 2. ANÁLISE DE INTENÇÃO CONTEXTUAL
        intent_data = self._analyze_contextual_intent(query, user_context)
        
        # 3. DETERMINAÇÃO DE URGÊNCIA
        urgency_level = self._determine_urgency(query)
        
        # 4. PERSONALIZAÇÃO BASEADA NO USUÁRIO
        personalization_factors = self._get_personalization_factors(user_context)
        
        # 5. ESTRATÉGIA DE RESPOSTA RECOMENDADA
        response_strategy = self._determine_response_strategy(
            complexity_score, intent_data, urgency_level, personalization_factors
        )
        
        result = {
            "complexity_score": complexity_score,
            "processing_mode": "complete" if complexity_score > 0.6 else "fast",
            "recommended_agent": intent_data["agent"],
            "intent_confidence": intent_data["confidence"],
            "urgency_level": urgency_level,
            "response_strategy": response_strategy,
            "personalization": personalization_factors,
            "estimated_time": self._estimate_response_time(complexity_score, response_strategy)
        }
        
        # Cache por 1 hora
        cache.set(cache_key, result, 3600)
        return result
    
    def _calculate_complexity_score(self, query: str) -> float:
        """Cálculo avançado de complexidade"""
        
        query_lower = query.lower()
        score = 0.5  # Base neutra
        
        # Fatores que aumentam complexidade
        complex_indicators = [
            (r'\b(análise|compare|explique|detalhe|completo|relatório)\b', 0.15),
            (r'\b(como funciona|por que|qual a diferença|me ensine)\b', 0.10),
            (r'\b(estratégia|implementar|planejar|desenvolver)\b', 0.10),
            (r'\?.*\?', 0.10),  # Múltiplas perguntas
            (r'\b(e também|além disso|primeiro|segundo|depois|simultaneamente)\b', 0.10),
            (r'.{150,}', 0.10),  # Query muito longa
            (r'\b(capacitação|trilha|desenvolvimento|certificação)\b', 0.08),
            (r'\b(dashboard|métricas|indicadores|performance)\b', 0.08)
        ]
        
        # Fatores que reduzem complexidade  
        simple_indicators = [
            (r'^(qual|quando|onde|quem)\s+.{1,30}[?]?$', -0.15),  # Perguntas diretas curtas
            (r'^(o que é|que é)\s+.{1,40}[?]?$', -0.10),  # Definições simples
            (r'\b(férias|licença|horário|benefício|vale|plano)\b', -0.10),  # FAQ comum
            (r'^.{1,50}[?]?$', -0.08),  # Query muito curta
            (r'^\b(sim|não|ok|obrigado|tchau|oi|olá)\b', -0.20)  # Respostas simples
        ]
        
        # Aplicar indicadores
        for pattern, weight in complex_indicators:
            if re.search(pattern, query_lower):
                score += weight
        
        for pattern, weight in simple_indicators:
            if re.search(pattern, query_lower):
                score += weight
        
        return max(0.0, min(1.0, score))
    
    def _analyze_contextual_intent(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Análise de intenção com contexto do usuário"""
        
        query_lower = query.lower()
        
        # Palavras-chave por agente com pesos
        agent_keywords = {
            "knight": {
                "strong": ["férias", "licença", "benefício", "política", "RH", "regulamento", "processo"],
                "medium": ["como", "qual", "quando", "posso", "dúvida", "informação"],
                "weak": ["empresa", "trabalho", "colaborador"]
            },
            "bard": {
                "strong": ["relatório", "análise", "dados", "métrica", "dashboard", "gráfico", "comparar"],
                "medium": ["mostrar", "visualizar", "estatística", "performance", "resultado"],
                "weak": ["número", "quantidade", "total"]
            },
            "wizard": {
                "strong": ["capacitação", "treinamento", "curso", "trilha", "aprender", "certificação"],
                "medium": ["desenvolver", "habilidade", "competência", "formação"],
                "weak": ["ensino", "educação", "conhecimento"]
            }
        }
        
        # Calcular scores por agente
        agent_scores = {}
        for agent, keywords in agent_keywords.items():
            score = 0.0
            for keyword in keywords["strong"]:
                if keyword in query_lower:
                    score += 0.3
            for keyword in keywords["medium"]:
                if keyword in query_lower:
                    score += 0.2
            for keyword in keywords["weak"]:
                if keyword in query_lower:
                    score += 0.1
            agent_scores[agent] = score
        
        # Contextualizar baseado no usuário
        if user_context.get('department') == 'TI':
            agent_scores["bard"] += 0.1  # TI tende a pedir mais análises
        elif user_context.get('department') == 'RH':
            agent_scores["knight"] += 0.1  # RH usa mais políticas
        
        if user_context.get('is_new_employee'):
            agent_scores["wizard"] += 0.15  # Novos funcionários precisam de capacitação
        
        # Determinar agente e confiança
        best_agent = max(agent_scores, key=agent_scores.get)
        best_score = agent_scores[best_agent]
        
        # Se scores muito próximos, usar knight como padrão
        second_best_score = sorted(agent_scores.values(), reverse=True)[1]
        if best_score - second_best_score < 0.1:
            best_agent = "knight"
            confidence = 0.6
        else:
            confidence = min(0.95, 0.5 + best_score)
        
        return {
            "agent": best_agent,
            "confidence": confidence,
            "scores": agent_scores
        }
    
    def _determine_urgency(self, query: str) -> str:
        """Determina urgência baseada em indicadores linguísticos"""
        
        query_lower = query.lower()
        
        # Indicadores de alta urgência
        high_urgency = [
            "urgente", "emergência", "agora", "imediato", "hoje", "problema",
            "não funciona", "erro", "falha", "bloqueado", "prazo"
        ]
        
        # Indicadores de média urgência
        medium_urgency = [
            "preciso", "necessário", "importante", "quando", "até quando",
            "deadline", "entrega", "reunião"
        ]
        
        # Indicadores de baixa urgência
        low_urgency = [
            "gostaria", "poderia", "seria possível", "no futuro", "eventualmente",
            "curiosidade", "dúvida"
        ]
        
        if any(indicator in query_lower for indicator in high_urgency):
            return "high"
        elif any(indicator in query_lower for indicator in medium_urgency):
            return "medium"
        elif any(indicator in query_lower for indicator in low_urgency):
            return "low"
        else:
            return "medium"  # Padrão
    
    def _get_personalization_factors(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fatores de personalização baseados no contexto do usuário"""
        
        factors = {
            "communication_style": "formal",  # Padrão corporativo
            "detail_level": "medium",
            "include_examples": True,
            "include_next_steps": True,
            "preferred_format": "structured"
        }
        
        # Personalizar baseado no cargo
        role = user_context.get('role', '').lower()
        if 'gerente' in role or 'coordenador' in role or 'supervisor' in role:
            factors["detail_level"] = "high"
            factors["include_strategic_view"] = True
        elif 'analista' in role or 'assistente' in role:
            factors["include_examples"] = True
            factors["detail_level"] = "high"
        elif 'estagiário' in role or 'júnior' in role:
            factors["include_examples"] = True
            factors["communication_style"] = "didático"
        
        # Personalizar baseado no departamento
        department = user_context.get('department', '').lower()
        if department in ['ti', 'tecnologia', 'desenvolvimento']:
            factors["preferred_format"] = "technical"
            factors["include_technical_details"] = True
        elif department in ['comercial', 'vendas']:
            factors["include_business_impact"] = True
        elif department in ['rh', 'recursos humanos']:
            factors["include_policy_references"] = True
        
        return factors
    
    def _determine_response_strategy(
        self, 
        complexity: float, 
        intent: Dict[str, Any], 
        urgency: str, 
        personalization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determina estratégia de resposta otimizada"""
        
        strategy = {
            "approach": "hybrid",  # hybrid, direct, analytical
            "tone": "professional",
            "structure": "standard",
            "include_sources": True,
            "include_alternatives": False,
            "follow_up_suggestions": True
        }
        
        # Ajustar baseado na complexidade
        if complexity > 0.7:
            strategy["approach"] = "analytical"
            strategy["structure"] = "detailed"
            strategy["include_alternatives"] = True
        elif complexity < 0.4:
            strategy["approach"] = "direct"
            strategy["structure"] = "concise"
        
        # Ajustar baseado na urgência
        if urgency == "high":
            strategy["structure"] = "action_focused"
            strategy["tone"] = "supportive"
            strategy["priority_info_first"] = True
        elif urgency == "low":
            strategy["include_educational_content"] = True
            strategy["structure"] = "comprehensive"
        
        # Ajustar baseado no agente recomendado
        if intent["agent"] == "bard":
            strategy["include_data_visualization_hints"] = True
            strategy["tone"] = "analytical"
        elif intent["agent"] == "wizard":
            strategy["include_learning_resources"] = True
            strategy["tone"] = "encouraging"
        
        return strategy
    
    def _estimate_response_time(self, complexity: float, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Estima tempo de resposta baseado na complexidade e estratégia"""
        
        base_time = 3  # segundos base
        
        # Ajustar por complexidade
        complexity_multiplier = 1 + (complexity * 2)
        
        # Ajustar por estratégia
        strategy_multiplier = 1.0
        if strategy["approach"] == "analytical":
            strategy_multiplier = 1.5
        elif strategy["structure"] == "detailed":
            strategy_multiplier = 1.3
        
        estimated_seconds = base_time * complexity_multiplier * strategy_multiplier
        
        return {
            "min_seconds": int(estimated_seconds * 0.8),
            "max_seconds": int(estimated_seconds * 1.5),
            "average_seconds": int(estimated_seconds)
        }
    
    def generate_optimized_prompt(
        self, 
        agent_type: str,
        query: str,
        context: str,
        user_context: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> str:
        """Gera prompt otimizado baseado na análise inteligente"""
        
        # System prompt personalizado
        system_prompt = self.prompt_lib.get_system_prompt(agent_type, user_context)
        
        # Instruções específicas baseadas na estratégia
        strategy_instructions = self._build_strategy_instructions(strategy)
        
        # Contexto formatado
        formatted_context = self._format_context(context, strategy)
        
        # Prompt final otimizado
        optimized_prompt = f"""{system_prompt}

{strategy_instructions}

CONTEXTO DISPONÍVEL:
{formatted_context}

CONSULTA DO USUÁRIO: {query}

Forneça uma resposta seguindo exatamente as diretrizes estabelecidas."""
        
        return optimized_prompt
    
    def _build_strategy_instructions(self, strategy: Dict[str, Any]) -> str:
        """Constrói instruções específicas baseadas na estratégia"""
        
        instructions = ["INSTRUÇÕES ESPECÍFICAS PARA ESTA CONSULTA:"]
        
        if strategy["approach"] == "analytical":
            instructions.append("- Forneça análise detalhada e aprofundada")
            instructions.append("- Inclua múltiplas perspectivas quando relevante")
        elif strategy["approach"] == "direct":
            instructions.append("- Seja direto e conciso")
            instructions.append("- Priorize a resposta principal")
        
        if strategy["structure"] == "detailed":
            instructions.append("- Use estrutura detalhada com seções claras")
            instructions.append("- Inclua exemplos práticos e casos de uso")
        elif strategy["structure"] == "concise":
            instructions.append("- Mantenha resposta concisa mas completa")
            instructions.append("- Foque nos pontos essenciais")
        
        if strategy.get("include_alternatives"):
            instructions.append("- Mencione alternativas ou opções adicionais")
        
        if strategy.get("priority_info_first"):
            instructions.append("- PRIORIDADE: Comece com a informação mais urgente")
        
        if strategy.get("include_learning_resources"):
            instructions.append("- Inclua recursos para aprendizado adicional")
        
        if strategy.get("include_data_visualization_hints"):
            instructions.append("- Sugira formas de visualizar os dados mencionados")
        
        return "\n".join(instructions)
    
    def _format_context(self, context: str, strategy: Dict[str, Any]) -> str:
        """Formata contexto baseado na estratégia"""
        
        if not context:
            return "Nenhum documento específico disponível para esta consulta."
        
        # Se estratégia é concisa, limitar contexto
        if strategy["structure"] == "concise":
            return context[:800] + ("..." if len(context) > 800 else "")
        
        # Se estratégia é detalhada, usar contexto completo
        return context
    
    def validate_response_quality(
        self, 
        response: str, 
        query: str, 
        strategy: Dict[str, Any],
        context: str = ""
    ) -> Dict[str, Any]:
        """Validação avançada de qualidade da resposta"""
        
        quality_metrics = {
            "overall_score": 0.0,
            "length_score": 0.0,
            "relevance_score": 0.0,
            "structure_score": 0.0,
            "professionalism_score": 0.0,
            "actionability_score": 0.0,
            "issues": [],
            "suggestions": []
        }
        
        # 1. Validar comprimento
        length_score = self._validate_response_length(response, strategy)
        quality_metrics["length_score"] = length_score
        
        # 2. Validar relevância
        relevance_score = self._validate_relevance(response, query, context)
        quality_metrics["relevance_score"] = relevance_score
        
        # 3. Validar estrutura
        structure_score = self._validate_structure(response, strategy)
        quality_metrics["structure_score"] = structure_score
        
        # 4. Validar profissionalismo
        professionalism_score = self._validate_professionalism(response)
        quality_metrics["professionalism_score"] = professionalism_score
        
        # 5. Validar orientação à ação
        actionability_score = self._validate_actionability(response, strategy)
        quality_metrics["actionability_score"] = actionability_score
        
        # Calcular score geral
        weights = {
            "length": 0.15,
            "relevance": 0.30,
            "structure": 0.20,
            "professionalism": 0.20,
            "actionability": 0.15
        }
        
        quality_metrics["overall_score"] = (
            length_score * weights["length"] +
            relevance_score * weights["relevance"] +
            structure_score * weights["structure"] +
            professionalism_score * weights["professionalism"] +
            actionability_score * weights["actionability"]
        )
        
        # Identificar problemas e sugestões
        quality_metrics["issues"], quality_metrics["suggestions"] = self._identify_quality_issues(
            quality_metrics, response, strategy
        )
        
        return quality_metrics
    
    def _validate_response_length(self, response: str, strategy: Dict[str, Any]) -> float:
        """Valida adequação do comprimento da resposta"""
        
        length = len(response)
        target_length = {
            "concise": (80, 300),
            "standard": (150, 600),
            "detailed": (300, 1200),
            "comprehensive": (400, 1500)
        }
        
        structure = strategy.get("structure", "standard")
        min_len, max_len = target_length.get(structure, target_length["standard"])
        
        if length < min_len * 0.5:
            return 0.2  # Muito curta
        elif length < min_len:
            return 0.6  # Um pouco curta
        elif min_len <= length <= max_len:
            return 1.0  # Ideal
        elif length <= max_len * 1.3:
            return 0.8  # Um pouco longa
        else:
            return 0.4  # Muito longa
    
    def _validate_relevance(self, response: str, query: str, context: str) -> float:
        """Valida relevância da resposta para a query"""
        
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        response_words = set(re.findall(r'\b\w+\b', response.lower()))
        
        # Remover palavras muito comuns
        stop_words = {"o", "a", "os", "as", "de", "da", "do", "das", "dos", "em", "para", "com", "por", "que", "e", "ou"}
        query_words -= stop_words
        response_words -= stop_words
        
        if not query_words:
            return 0.5
        
        # Calcular sobreposição
        overlap = len(query_words & response_words)
        relevance_ratio = overlap / len(query_words)
        
        # Penalizar se resposta parece genérica
        generic_phrases = [
            "desculpe", "não tenho informações", "não posso ajudar",
            "tente novamente", "erro interno"
        ]
        
        if any(phrase in response.lower() for phrase in generic_phrases):
            relevance_ratio *= 0.3
        
        return min(1.0, relevance_ratio * 1.5)
    
    def _validate_structure(self, response: str, strategy: Dict[str, Any]) -> float:
        """Valida estrutura da resposta"""
        
        score = 0.5  # Base
        
        # Verificar se tem estrutura clara
        if re.search(r'\n\s*\n', response):  # Parágrafos separados
            score += 0.2
        
        # Verificar listas ou enumeração
        if re.search(r'^\s*[-*•]\s+', response, re.MULTILINE) or re.search(r'^\s*\d+\.\s+', response, re.MULTILINE):
            score += 0.15
        
        # Verificar seções/tópicos
        if re.search(r'^[A-Z][^.!?]*:$', response, re.MULTILINE):
            score += 0.15
        
        # Penalizar se muito desorganizada
        sentences = re.split(r'[.!?]+', response)
        if len(sentences) > 10 and not re.search(r'\n', response):
            score -= 0.2  # Texto corrido muito longo
        
        return min(1.0, score)
    
    def _validate_professionalism(self, response: str) -> float:
        """Valida tom profissional"""
        
        score = 0.8  # Base alta para tom corporativo
        
        # Verificar saudações profissionais
        if re.search(r'\b(prezado|caro|atenciosamente|cordialmente)\b', response, re.IGNORECASE):
            score += 0.1
        
        # Penalizar linguagem muito informal
        informal_indicators = [
            r'\b(cara|mano|galera|pessoal)\b',
            r'\b(tipo assim|né|tá bom)\b',
            r'!{2,}',  # Múltiplas exclamações
            r'\b(super|mega|hiper)\b'
        ]
        
        for pattern in informal_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                score -= 0.15
        
        # Verificar linguagem corporativa apropriada
        professional_indicators = [
            r'\b(recomendo|sugiro|orientamos|informamos)\b',
            r'\b(política|procedimento|regulamento|diretrizes)\b',
            r'\b(departamento|setor|equipe|colaborador)\b'
        ]
        
        for pattern in professional_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _validate_actionability(self, response: str, strategy: Dict[str, Any]) -> float:
        """Valida se a resposta é orientada à ação"""
        
        if not strategy.get("include_next_steps", True):
            return 1.0  # Não esperado para esta estratégia
        
        score = 0.3  # Base baixa
        
        # Verificar verbos de ação
        action_verbs = [
            r'\b(acesse|consulte|procure|entre em contato|dirija-se)\b',
            r'\b(preencha|envie|solicite|apresente|compareça)\b',
            r'\b(verifique|confirme|validar|acompanhe)\b'
        ]
        
        for pattern in action_verbs:
            if re.search(pattern, response, re.IGNORECASE):
                score += 0.2
        
        # Verificar próximos passos explícitos
        next_steps_indicators = [
            r'próxim[oa]s? passos?',
            r'para [^.]{1,50}:\s*\n',
            r'\b(primeiro|segundo|em seguida|depois|finalmente)\b'
        ]
        
        for pattern in next_steps_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                score += 0.25
        
        # Verificar contatos ou recursos
        if re.search(r'contato|telefone|email|@|setor|departamento', response, re.IGNORECASE):
            score += 0.15
        
        return min(1.0, score)
    
    def _identify_quality_issues(
        self, 
        metrics: Dict[str, Any], 
        response: str, 
        strategy: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Identifica problemas e sugestões de melhoria"""
        
        issues = []
        suggestions = []
        
        # Problemas de comprimento
        if metrics["length_score"] < 0.5:
            if len(response) < 80:
                issues.append("Resposta muito curta")
                suggestions.append("Expandir com mais detalhes e contexto")
            else:
                issues.append("Resposta muito longa")
                suggestions.append("Resumir pontos principais")
        
        # Problemas de relevância
        if metrics["relevance_score"] < 0.6:
            issues.append("Baixa relevância para a consulta")
            suggestions.append("Focar mais especificamente na pergunta do usuário")
        
        # Problemas de estrutura
        if metrics["structure_score"] < 0.6:
            issues.append("Estrutura pouco clara")
            suggestions.append("Organizar em parágrafos ou tópicos distintos")
        
        # Problemas de profissionalismo
        if metrics["professionalism_score"] < 0.7:
            issues.append("Tom pouco profissional")
            suggestions.append("Usar linguagem mais corporativa e formal")
        
        # Problemas de acionabilidade
        if metrics["actionability_score"] < 0.5:
            issues.append("Falta de orientação prática")
            suggestions.append("Incluir próximos passos específicos")
        
        return issues, suggestions


# Instância singleton
intelligent_behavior = IntelligentBehavior()