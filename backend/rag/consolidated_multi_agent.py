"""
Consolidated Multi-Agent Service - Sistema único com adaptação automática
Combina todas as funcionalidades em um arquivo:
- LangGraph para queries complexas (qualidade)
- Sistema otimizado para queries simples (velocidade)
- Adaptação automática baseada na complexidade
- Cache inteligente e fallbacks robustos
"""
import time
import re
import json
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
from django.core.cache import cache

# LangGraph imports
from langgraph.graph import StateGraph, START, END

# Services
from .hybrid_vector_service import HybridVectorService
from .services import BM25SearchService
from .llm_providers import LLMManager
from .agentic_config import get_config
from .intelligent_behavior import intelligent_behavior
from .behavior_monitoring import behavior_monitor


class MultiAgentState(TypedDict):
    """Estado compartilhado entre todos os agentes"""
    query: str
    user: Any
    user_profile: Dict[str, Any]
    agent_used: str
    search_results: List[Dict]
    response: str
    metadata: Dict[str, Any]
    execution_path: List[str]
    quality_score: float
    processing_mode: str  # 'fast' ou 'complete'


class ConsolidatedMultiAgentService:
    """Sistema multi-agent unificado com adaptação automática"""
    
    def __init__(self):
        # Core services
        self.vector_search = HybridVectorService()
        self.bm25_search = BM25SearchService()
        self.llm_manager = LLMManager()
        self.config = get_config()
        
        # LangGraph state machine para queries complexas
        self.complex_graph = self._build_complex_graph()
        
        # Cache para análise de intenção e resultados
        self._intent_cache = {}
    
    def process_query(
        self, 
        query: str, 
        user: Any = None,
        user_profile: Dict[str, Any] = None,
        force_mode: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Ponto de entrada principal - decide automaticamente entre fast/complete"""
        
        start_time = time.time()
        user_profile = user_profile or {}
        
        try:
            # 1. ANÁLISE DE COMPLEXIDADE
            if force_mode:
                complexity_mode = force_mode
            else:
                complexity_mode = self._analyze_query_complexity(query, user_profile)
            
            # 2. PROCESSAMENTO BASEADO NA COMPLEXIDADE
            if complexity_mode == 'fast':
                result = self._process_fast_mode(query, user, user_profile)
            else:
                result = self._process_complete_mode(query, user, user_profile)
            
            # 3. METADATA FINAL
            total_time = int((time.time() - start_time) * 1000)
            result['metadata'].update({
                'processing_mode': complexity_mode,
                'total_duration_ms': total_time,
                'consolidated_system': True
            })
            
            # 4. MONITORAMENTO DE COMPORTAMENTO
            try:
                behavior_monitor.log_response_metrics(
                    query=query,
                    agent_used=result.get('agent_used', 'unknown'),
                    response=result.get('response', ''),
                    analysis=result.get('metadata', {}).get('intelligent_analysis', {}),
                    quality_validation=result.get('metadata', {}).get('quality_validation', {}),
                    processing_time_ms=total_time,
                    user_context=user_profile
                )
            except Exception as e:
                # Log erro mas não falha o processamento principal
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Erro no monitoramento de comportamento: {str(e)}")
            
            return result
            
        except Exception as e:
            return self._handle_error(query, str(e), int((time.time() - start_time) * 1000))
    
    def _analyze_query_complexity(self, query: str, user_profile: Dict[str, Any] = None) -> str:
        """Análise inteligente de complexidade usando sistema refinado"""
        
        # Usar sistema inteligente de comportamento
        analysis = intelligent_behavior.analyze_query_intelligence(query, user_profile or {})
        
        return analysis["processing_mode"]
    
    def _process_fast_mode(self, query: str, user: Any, user_profile: Dict) -> Dict[str, Any]:
        """Modo rápido - sem LangGraph, direto ao agente com comportamento inteligente"""
        
        # Análise inteligente completa
        analysis = intelligent_behavior.analyze_query_intelligence(query, user_profile)
        target_agent = analysis["recommended_agent"]
        
        # Processamento direto por agente com comportamento refinado
        if target_agent == "bard":
            result = self._bard_fast_response(query, user_profile, analysis)
        elif target_agent == "wizard":
            result = self._wizard_fast_response(query, user_profile, analysis)
        else:
            result = self._knight_fast_response(query, user, analysis)
        
        return {
            "query": query,
            "response": result.get("response", "Erro no processamento"),
            "agent_used": target_agent,
            "execution_path": [f"{target_agent}_fast_intelligent"],
            "search_results": result.get("search_results", []),
            "metadata": {
                "provider_used": result.get("provider_used", "unknown"),
                "task_type": result.get("task_type", "general"),
                "performance_mode": "fast",
                "is_optimized": True,
                "intelligent_analysis": analysis,
                "quality_validation": result.get("quality_validation", {})
            }
        }
    
    def _process_complete_mode(self, query: str, user: Any, user_profile: Dict) -> Dict[str, Any]:
        """Modo completo - usa LangGraph para qualidade máxima"""
        
        # Estado inicial
        initial_state = MultiAgentState(
            query=query,
            user=user,
            user_profile=user_profile,
            agent_used="knight",
            search_results=[],
            response="",
            metadata={},
            execution_path=[],
            quality_score=0.0,
            processing_mode="complete"
        )
        
        # Executar grafo LangGraph
        final_state = self.complex_graph.invoke(initial_state)
        
        return {
            "query": final_state["query"],
            "response": final_state["response"],
            "agent_used": final_state["agent_used"],
            "execution_path": final_state["execution_path"],
            "search_results": final_state["search_results"],
            "metadata": {
                **final_state["metadata"],
                "performance_mode": "complete",
                "quality_score": final_state["quality_score"],
                "langgraph_processing": True
            }
        }
    
    def _build_complex_graph(self) -> StateGraph:
        """Constrói o grafo LangGraph para processamento completo"""
        
        graph = StateGraph(MultiAgentState)
        
        # Nodes
        graph.add_node("knight_supervisor", self._knight_supervisor_node)
        graph.add_node("bard_agent", self._bard_agent_node)
        graph.add_node("wizard_agent", self._wizard_agent_node)
        graph.add_node("knight_rag", self._knight_rag_node)
        graph.add_node("quality_check", self._quality_check_node)
        graph.add_node("finalizer", self._finalizer_node)
        
        # Edges
        graph.add_edge(START, "knight_supervisor")
        graph.add_conditional_edges(
            "knight_supervisor",
            self._routing_decision,
            {
                "bard": "bard_agent",
                "wizard": "wizard_agent",
                "knight": "knight_rag"
            }
        )
        
        # Todos os agentes vão para quality_check
        graph.add_edge("bard_agent", "quality_check")
        graph.add_edge("wizard_agent", "quality_check")
        graph.add_edge("knight_rag", "quality_check")
        
        # Quality check decide se vai para finalizer ou refaz
        graph.add_conditional_edges(
            "quality_check",
            self._quality_decision,
            {
                "finalize": "finalizer",
                "retry_knight": "knight_rag"
            }
        )
        
        graph.add_edge("finalizer", END)
        
        return graph.compile()
    
    def _knight_supervisor_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Knight atua como supervisor analisando a query"""
        
        query = state["query"]
        state["execution_path"].append("knight_supervisor")
        
        # Análise detalhada com LLM
        analysis_prompt = f"""
        Analise esta consulta e determine qual agente deve processá-la:
        
        CONSULTA: {query}
        
        AGENTES DISPONÍVEIS:
        - KNIGHT: Consultas gerais sobre documentos corporativos, políticas, RH
        - BARD: Relatórios, análises de dados, métricas, dashboards
        - WIZARD: Capacitações, trilhas de aprendizado, onboarding, certificações
        
        Responda APENAS com: KNIGHT, BARD ou WIZARD
        """
        
        llm_response = self.llm_manager.generate_response(
            prompt=analysis_prompt,
            max_tokens=10,
            temperature=0.0
        )
        
        if llm_response["success"]:
            agent_decision = llm_response["response"].strip().upper()
            if agent_decision in ["BARD", "WIZARD"]:
                state["agent_used"] = agent_decision.lower()
            else:
                state["agent_used"] = "knight"
        else:
            state["agent_used"] = "knight"
        
        state["metadata"]["supervisor_analysis"] = {
            "decision": state["agent_used"],
            "llm_success": llm_response["success"]
        }
        
        return state
    
    def _bard_agent_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Agente Bard - especialista em relatórios e análises"""
        
        state["execution_path"].append("bard_complete")
        query = state["query"]
        user_profile = state["user_profile"]
        
        # Buscar dados relevantes primeiro
        search_results = self.vector_search.search(query, k=3)
        state["search_results"] = search_results
        
        # Preparar contexto para análise
        context = self._prepare_context(search_results)
        
        # Prompt completo para Bard
        bard_prompt = f"""
        Você é o agente BARD, especialista em análises e relatórios corporativos.
        
        CONSULTA DO USUÁRIO: {query}
        USUÁRIO: {user_profile.get('name', 'Usuário')}
        
        CONTEXTO DISPONÍVEL:
        {context}
        
        Como especialista em análise de dados, forneça:
        1. Análise detalhada da consulta
        2. Insights baseados nos dados disponíveis
        3. Recomendações específicas
        4. Sugestões de métricas adicionais se necessário
        
        Responda de forma completa e profissional, focando em análise de dados.
        """
        
        llm_response = self.llm_manager.generate_response(
            prompt=bard_prompt,
            max_tokens=400,
            temperature=0.7
        )
        
        if llm_response["success"]:
            enhanced_response = f"""📊 **ANÁLISE BARD COMPLETA**

{llm_response['response']}

**Para análises interativas:**
🎭 [Central de Relatórios](/bard) - Gráficos, dashboards e exportação"""
            
            state["response"] = enhanced_response
            state["quality_score"] = 0.8  # Alto score para resposta completa
        else:
            state["response"] = "Erro ao gerar análise. Tente novamente."
            state["quality_score"] = 0.3
        
        state["metadata"]["bard_processing"] = {
            "search_results_count": len(search_results),
            "llm_success": llm_response["success"],
            "provider_used": llm_response.get("provider", "unknown")
        }
        
        return state
    
    def _wizard_agent_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Agente Wizard - especialista em capacitações"""
        
        state["execution_path"].append("wizard_complete")
        query = state["query"]
        user_profile = state["user_profile"]
        
        # Buscar conteúdo educacional
        search_results = self.vector_search.search(query, k=3)
        state["search_results"] = search_results
        
        context = self._prepare_context(search_results)
        
        # Prompt completo para Wizard
        wizard_prompt = f"""
        Você é o agente WIZARD, especialista em capacitações e desenvolvimento.
        
        CONSULTA DO USUÁRIO: {query}
        USUÁRIO: {user_profile.get('name', 'Usuário')}
        
        CONTEXTO DISPONÍVEL:
        {context}
        
        Como especialista em capacitações, forneça:
        1. Análise das necessidades de desenvolvimento
        2. Trilha de aprendizado personalizada
        3. Recursos e materiais recomendados
        4. Cronograma sugerido
        5. Métodos de acompanhamento
        
        Responda com um plano completo de capacitação.
        """
        
        llm_response = self.llm_manager.generate_response(
            prompt=wizard_prompt,
            max_tokens=400,
            temperature=0.7
        )
        
        if llm_response["success"]:
            enhanced_response = f"""🧙 **PLANO WIZARD COMPLETO**

{llm_response['response']}

**Para trilhas personalizadas:**
🧙 [Capacitações](/wizard) - Trilhas por cargo, certificações e acompanhamento"""
            
            state["response"] = enhanced_response
            state["quality_score"] = 0.8
        else:
            state["response"] = "Erro ao gerar plano. Tente novamente."
            state["quality_score"] = 0.3
        
        state["metadata"]["wizard_processing"] = {
            "search_results_count": len(search_results),
            "llm_success": llm_response["success"],
            "provider_used": llm_response.get("provider", "unknown")
        }
        
        return state
    
    def _knight_rag_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Knight RAG completo com busca híbrida"""
        
        state["execution_path"].append("knight_rag_complete")
        query = state["query"]
        user = state["user"]
        
        # Busca híbrida completa
        search_results = self.vector_search.search(query, k=5)
        state["search_results"] = search_results
        
        if not search_results:
            state["response"] = f"Não encontrei informações específicas sobre '{query}'. Como posso ajudá-lo de outra forma?"
            state["quality_score"] = 0.4
            return state
        
        # Contexto completo
        context = self._prepare_context(search_results, max_length=2000)
        
        # Prompt completo para Knight
        knight_prompt = f"""
        Você é o KNIGHT, assistente corporativo especialista em documentos internos.
        
        PERGUNTA: {query}
        
        CONTEXTO DOS DOCUMENTOS:
        {context}
        
        Forneça uma resposta completa e precisa baseada nos documentos.
        Seja detalhado, mas mantenha a clareza e objetividade.
        Se necessário, cite os documentos relevantes.
        """
        
        llm_response = self.llm_manager.generate_response(
            prompt=knight_prompt,
            max_tokens=500,
            temperature=0.4
        )
        
        if llm_response["success"]:
            state["response"] = llm_response["response"]
            state["quality_score"] = 0.7
        else:
            state["response"] = "Erro ao gerar resposta. Tente reformular a pergunta."
            state["quality_score"] = 0.3
        
        state["metadata"]["knight_processing"] = {
            "search_results_count": len(search_results),
            "context_length": len(context),
            "llm_success": llm_response["success"],
            "provider_used": llm_response.get("provider", "unknown")
        }
        
        return state
    
    def _quality_check_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Verifica qualidade da resposta"""
        
        state["execution_path"].append("quality_check")
        
        response = state["response"]
        quality_score = state["quality_score"]
        
        # Critérios básicos de qualidade
        if not response or len(response) < 50:
            quality_score -= 0.3
        
        if "erro" in response.lower() or "desculpe" in response.lower():
            quality_score -= 0.2
        
        if len(response) > 100 and len(state["search_results"]) > 0:
            quality_score += 0.1
        
        state["quality_score"] = max(0.0, min(1.0, quality_score))
        
        return state
    
    def _finalizer_node(self, state: MultiAgentState) -> Dict[str, Any]:
        """Finaliza o processamento"""
        
        state["execution_path"].append("finalizer")
        state["metadata"]["final_quality_score"] = state["quality_score"]
        state["metadata"]["execution_path"] = state["execution_path"]
        
        return state
    
    def _routing_decision(self, state: MultiAgentState) -> str:
        """Decisão de roteamento baseada no agente escolhido"""
        return state["agent_used"]
    
    def _quality_decision(self, state: MultiAgentState) -> str:
        """Decisão baseada na qualidade da resposta"""
        if state["quality_score"] >= 0.5:
            return "finalize"
        else:
            return "retry_knight"
    
    # MÉTODOS AUXILIARES RÁPIDOS (para modo fast)
    
    def _fast_intent_analysis(self, query: str) -> str:
        """Análise de intenção otimizada com cache + heurísticas"""
        
        cache_key = f"intent_fast_{hash(query)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        query_lower = query.lower()
        
        # FAQ instantâneo
        faq_keywords = {
            'férias': 'knight', 'home office': 'knight', 'horário': 'knight',
            'licença': 'knight', 'benefício': 'knight', 'vale': 'knight'
        }
        
        for keyword, agent in faq_keywords.items():
            if keyword in query_lower:
                cache.set(cache_key, agent, 3600)
                return agent
        
        # Keywords por agente
        bard_keywords = ['relatório', 'análise', 'métrica', 'dados', 'dashboard', 'gráfico']
        wizard_keywords = ['capacitação', 'treinamento', 'curso', 'trilha', 'onboarding']
        
        if any(kw in query_lower for kw in bard_keywords):
            intent = "bard"
        elif any(kw in query_lower for kw in wizard_keywords):
            intent = "wizard"
        else:
            intent = "knight"
        
        cache.set(cache_key, intent, 3600)
        return intent
    
    def _knight_fast_response(self, query: str, user: Any, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Knight RAG ultra-rápido com comportamento inteligente"""
        
        cache_key = f"knight_intelligent_{hash(query)}_{hash(str(analysis.get('personalization', {})))}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Busca semântica rápida
        search_results = self.vector_search.search(query, k=2)
        
        if not search_results:
            result = {
                "response": f"Não encontrei informações específicas sobre '{query}'. Como posso ajudá-lo de outra forma?",
                "search_results": [],
                "provider_used": "no_results",
                "task_type": "general"
            }
            cache.set(cache_key, result, 1800)
            return result
        
        # Contexto formatado
        context = self._prepare_context(search_results, max_length=600)
        
        # Usar análise inteligente para prompt otimizado
        user_context = {
            'name': getattr(user, 'name', 'Colaborador') if user else 'Colaborador',
            'department': analysis.get('personalization', {}).get('department'),
            'role': analysis.get('personalization', {}).get('role')
        }
        
        optimized_prompt = intelligent_behavior.generate_optimized_prompt(
            agent_type="knight",
            query=query,
            context=context,
            user_context=user_context,
            strategy=analysis["response_strategy"]
        )
        
        llm_response = self.llm_manager.generate_response(
            prompt=optimized_prompt,
            max_tokens=200,
            temperature=0.3
        )
        
        response_text = llm_response.get("response", "Erro ao gerar resposta")
        
        # Validar qualidade da resposta
        quality_validation = intelligent_behavior.validate_response_quality(
            response_text, query, analysis["response_strategy"], context
        )
        
        result = {
            "response": response_text,
            "search_results": search_results,
            "provider_used": llm_response.get("provider", "unknown"),
            "task_type": "general",
            "quality_validation": quality_validation
        }
        
        cache.set(cache_key, result, 1800)
        return result
    
    def _bard_fast_response(self, query: str, user_profile: Dict, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Bard resposta rápida e personalizada com comportamento inteligente"""
        
        # Contexto do usuário para personalização
        user_context = {
            'name': user_profile.get('name', 'Colaborador'),
            'department': user_profile.get('department'),
            'role': user_profile.get('role')
        }
        
        # Prompt otimizado usando sistema inteligente
        optimized_prompt = intelligent_behavior.generate_optimized_prompt(
            agent_type="bard",
            query=query,
            context="",  # Bard fast mode sem contexto de documentos
            user_context=user_context,
            strategy=analysis["response_strategy"]
        )
        
        llm_response = self.llm_manager.generate_response(
            prompt=optimized_prompt,
            max_tokens=150,
            temperature=0.7
        )
        
        response_text = llm_response.get('response', '')
        
        if llm_response["success"] and response_text:
            enhanced_response = f"""📊 **ANÁLISE BARD - {user_context['name']}**

{response_text}

🎭 [Central de Relatórios](/bard) - Para análise completa com gráficos interativos"""
        else:
            enhanced_response = f"""📊 **ANÁLISE BARD - {user_context['name']}**

Sua consulta sobre "{query}" requer análise de dados especializada.

🎭 [Central de Relatórios](/bard) - Para relatórios personalizados com métricas detalhadas"""
        
        # Validar qualidade
        quality_validation = intelligent_behavior.validate_response_quality(
            enhanced_response, query, analysis["response_strategy"]
        )
        
        return {
            "response": enhanced_response,
            "search_results": [],
            "provider_used": llm_response.get("provider", "fallback"),
            "task_type": "report",
            "quality_validation": quality_validation
        }
    
    def _wizard_fast_response(self, query: str, user_profile: Dict, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Wizard resposta rápida e personalizada com comportamento inteligente"""
        
        # Contexto do usuário para personalização
        user_context = {
            'name': user_profile.get('name', 'Colaborador'),
            'department': user_profile.get('department'),
            'role': user_profile.get('role'),
            'is_new_employee': user_profile.get('is_new', False)
        }
        
        # Prompt otimizado usando sistema inteligente
        optimized_prompt = intelligent_behavior.generate_optimized_prompt(
            agent_type="wizard",
            query=query,
            context="",  # Wizard fast mode sem contexto de documentos
            user_context=user_context,
            strategy=analysis["response_strategy"]
        )
        
        llm_response = self.llm_manager.generate_response(
            prompt=optimized_prompt,
            max_tokens=150,
            temperature=0.7
        )
        
        response_text = llm_response.get('response', '')
        
        if llm_response["success"] and response_text:
            enhanced_response = f"""🧙 **PLANO WIZARD - {user_context['name']}**

{response_text}

🧙 [Trilha de Capacitação](/wizard) - Para plano completo e acompanhamento personalizado"""
        else:
            enhanced_response = f"""🧙 **PLANO WIZARD - {user_context['name']}**

Sua consulta sobre "{query}" indica necessidade de capacitação personalizada para sua função.

🧙 [Trilha de Capacitação](/wizard) - Para criar trilha específica com certificações"""
        
        # Validar qualidade
        quality_validation = intelligent_behavior.validate_response_quality(
            enhanced_response, query, analysis["response_strategy"]
        )
        
        return {
            "response": enhanced_response,
            "search_results": [],
            "provider_used": llm_response.get("provider", "fallback"),
            "task_type": "training",
            "quality_validation": quality_validation
        }
    
    def _prepare_context(self, search_results: List[Dict], max_length: int = 1000) -> str:
        """Prepara contexto dos resultados de busca"""
        
        if not search_results:
            return "Nenhum documento relevante encontrado."
        
        context_parts = []
        current_length = 0
        
        for result in search_results:
            content = result.get('content', '')
            if current_length + len(content) <= max_length:
                context_parts.append(content)
                current_length += len(content)
            else:
                # Adicionar parcialmente se couber
                remaining = max_length - current_length
                if remaining > 100:
                    context_parts.append(content[:remaining] + "...")
                break
        
        return '\n\n'.join(context_parts)
    
    def _handle_error(self, query: str, error: str, duration_ms: int) -> Dict[str, Any]:
        """Tratamento de erro padronizado"""
        
        return {
            "query": query,
            "response": "Desculpe, ocorreu um erro interno. Tente novamente em alguns momentos.",
            "agent_used": "error",
            "execution_path": ["error"],
            "search_results": [],
            "metadata": {
                "error": error,
                "total_duration_ms": duration_ms,
                "consolidated_system": True
            }
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema consolidado"""
        
        return {
            "consolidated_system": True,
            "modes": {
                "fast": "Queries simples - 3-8s",
                "complete": "Queries complexas - 10-20s com LangGraph"
            },
            "agents": ["knight", "bard", "wizard"],
            "features": {
                "adaptive_complexity": True,
                "langgraph_integration": True,
                "intelligent_cache": True,
                "multi_provider_llm": True,
                "hybrid_vector_search": True
            },
            "performance": {
                "fast_mode_target": "3-8 seconds",
                "complete_mode_target": "10-20 seconds",
                "cache_hit_target": "< 1 second"
            }
        }


# Instância singleton consolidada
consolidated_multi_agent_service = ConsolidatedMultiAgentService()