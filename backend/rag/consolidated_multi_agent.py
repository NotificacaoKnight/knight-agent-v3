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
import hashlib
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
# Imports removidos: intelligent_behavior, behavior_monitoring, intelligent_cache

# Cache global para serviços singleton
_GLOBAL_SERVICE_CACHE = {}

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
        import logging
        self.logger = logging.getLogger(__name__)
        
        try:
            # Core services com cache singleton
            self.vector_search = self._get_cached_service('vector_search', HybridVectorService)
            self.bm25_search = self._get_cached_service('bm25_search', BM25SearchService)
            self.llm_manager = self._get_cached_service('llm_manager', LLMManager)
            self.config = get_config()
            
            # LangGraph state machine para queries complexas
            self.complex_graph = self._build_complex_graph()
            
            # Cache para análise de intenção e resultados
            self._intent_cache = {}
            
            self.logger.info("ConsolidatedMultiAgentService initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing ConsolidatedMultiAgentService: {str(e)}")
            # Inicializar com valores padrão para não quebrar
            self.vector_search = None
            self.bm25_search = None
            self.llm_manager = None
            self.config = None
            self.complex_graph = None
            self._intent_cache = {}
    
    def _get_cached_service(self, service_name: str, service_class):
        """Obtém serviço do cache global ou cria novo"""
        global _GLOBAL_SERVICE_CACHE
        
        if service_name not in _GLOBAL_SERVICE_CACHE:
            _GLOBAL_SERVICE_CACHE[service_name] = service_class()
            
        return _GLOBAL_SERVICE_CACHE[service_name]
    
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
        
        # Verificação de segurança
        if not self.llm_manager:
            self.logger.error("LLM Manager not initialized, using fallback response")
            return self._get_fallback_response(query, force_mode, start_time)
        
        try:
            
            # 2. FORÇAR AGENTE ESPECÍFICO
            if force_mode in ['wizard', 'bard']:
                result = self._process_agent_specific(query, force_mode, user, user_profile)
            elif force_mode == 'fast':
                result = self._process_fast_mode(query, user, user_profile)
            elif force_mode == 'complete':
                result = self._process_complete_mode(query, user, user_profile)
            else:
                # 3. ANÁLISE DE COMPLEXIDADE AUTOMÁTICA
                complexity_mode = self._analyze_query_complexity(query, user_profile)
                
                if complexity_mode == 'fast':
                    result = self._process_fast_mode(query, user, user_profile)
                else:
                    result = self._process_complete_mode(query, user, user_profile)
            
            # 3. METADATA FINAL
            total_time = int((time.time() - start_time) * 1000)
            
            # Determinar o processing_mode usado
            if force_mode:
                processing_mode = force_mode
            else:
                processing_mode = complexity_mode if 'complexity_mode' in locals() else 'auto'
            
            result['metadata'].update({
                'processing_mode': processing_mode,
                'total_duration_ms': total_time,
                'consolidated_system': True
            })
            
            # Garantir campos obrigatórios
            if 'useful_links' not in result:
                result['useful_links'] = []
            if 'downloadable_documents' not in result:
                result['downloadable_documents'] = []
            
            # Monitoramento simplificado (logs básicos)
            try:
                agent_used = result.get('agent_used', 'unknown')
                print(f"🤖 Agent {agent_used} processed query in {total_time}ms")
            except Exception as e:
                pass
            
            return result
            
        except Exception as e:
            return self._handle_error(query, str(e), int((time.time() - start_time) * 1000))
    
    
    def _process_agent_specific(self, query: str, agent_type: str, user: Any, user_profile: Dict) -> Dict[str, Any]:
        """Processa com agente específico (wizard ou bard)"""
        
        try:
            if agent_type == "wizard":
                result = self._wizard_fast_response(query, user_profile, {"agent_forced": True})
            elif agent_type == "bard":
                result = self._bard_fast_response(query, user_profile, {"agent_forced": True})
            else:
                # Fallback para knight
                result = self._knight_fast_response(query, user, {"agent_forced": True})
            
            # Garantir estrutura completa
            return {
                "query": query,
                "response": result.get("response", "Erro no processamento"),
                "agent_used": agent_type,
                "execution_path": [f"{agent_type}_forced"],
                "search_results": result.get("search_results", []),
                "metadata": {
                    "provider_used": result.get("metadata", {}).get("provider_used", result.get("provider_used", "unknown")),
                    "task_type": result.get("task_type", "general"),
                    "performance_mode": "agent_specific",
                    "forced_agent": agent_type,
                    "quality_validation": result.get("quality_validation", {})
                },
                "useful_links": result.get("useful_links", []),
                "downloadable_documents": result.get("downloadable_documents", [])
            }
        except Exception as e:
            self.logger.error(f"Error in _process_agent_specific: {str(e)}")
            # Retornar resposta de fallback mockada
            if agent_type == "wizard":
                response = "🧙 Sou o Wizard! Posso ajudar com cursos, treinamentos e desenvolvimento profissional. O que você gostaria de aprender?"
            elif agent_type == "bard":
                response = "🎭 Sou o Bard! Especialista em análises e relatórios. Que dados você precisa analisar?"
            else:
                response = "⚔️ Sou o Knight, seu assistente de RH. Como posso ajudar?"
            
            return {
                "query": query,
                "response": response,
                "agent_used": agent_type,
                "execution_path": [f"{agent_type}_fallback"],
                "search_results": [],
                "metadata": {
                    "provider_used": "fallback_mock",
                    "task_type": "general",
                    "performance_mode": "agent_specific",
                    "forced_agent": agent_type,
                    "error": str(e)
                },
                "useful_links": [],
                "downloadable_documents": []
            }
    
    def _analyze_query_complexity(self, query: str, user_profile: Dict[str, Any] = None) -> str:
        """Análise inteligente de complexidade usando sistema refinado"""
        
        # Análise simples de complexidade
        analysis = self._simple_complexity_analysis(query, user_profile or {})
        
        return analysis["processing_mode"]
    
    def _simple_complexity_analysis(self, query: str, user_profile: Dict) -> Dict[str, Any]:
        """Análise simplificada de complexidade e agente apropriado"""
        query_lower = query.lower()
        
        # Análise de agente
        if any(keyword in query_lower for keyword in ['análise', 'dados', 'relatório', 'métrica', 'dashboard', 'gráfico']):
            recommended_agent = "bard"
        elif any(keyword in query_lower for keyword in ['capacitação', 'treinamento', 'curso', 'liderança', 'desenvolvimento']):
            recommended_agent = "wizard"
        else:
            recommended_agent = "knight"
        
        # Análise de complexidade
        complexity_indicators = len([word for word in ['análise', 'comparar', 'histórico', 'estratégico'] if word in query_lower])
        processing_mode = "complete" if complexity_indicators > 1 or len(query.split()) > 15 else "fast"
        
        return {
            "recommended_agent": recommended_agent,
            "processing_mode": processing_mode,
            "complexity_score": complexity_indicators / 4.0,
            "response_strategy": {"conversational": True, "analytical": recommended_agent == "bard"}
        }
    
    def _process_fast_mode(self, query: str, user: Any, user_profile: Dict) -> Dict[str, Any]:
        """Modo rápido - sem LangGraph, direto ao agente com comportamento inteligente"""
        
        # Análise simples de agente apropriado
        analysis = self._simple_complexity_analysis(query, user_profile)
        target_agent = analysis.get("recommended_agent", "knight")
        
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
        """Knight RAG natural e dinâmico com personalidade adaptativa"""
        
        # Usar cache inteligente
        user_context = {
            'name': getattr(user, 'name', 'Colaborador') if user else 'Colaborador',
            'department': analysis.get('personalization', {}).get('department'),
            'role': analysis.get('personalization', {}).get('role')
        }
        
        # Cache básico
        cache_key = f"knight_{hashlib.md5(query.encode()).hexdigest()}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return cached_response
        
        # Busca semântica rápida
        search_results = self.vector_search.search(query, k=3)
        
        if not search_results:
            # Respostas naturais quando não há contexto
            no_context_responses = [
                f"Não encontrei informações específicas sobre '{query}' nos nossos documentos. Que tal me dar mais detalhes sobre o que você precisa?",
                f"Hmm, sobre '{query}' não tenho informações documentadas aqui. Pode me explicar melhor sua situação?",
                f"Não vejo nada específico sobre '{query}' na nossa base. Como posso te ajudar de outra forma?"
            ]
            
            result = {
                "response": random.choice(no_context_responses),
                "search_results": [],
                "provider_used": "no_results_natural",
                "task_type": "general"
            }
            cache.set(cache_key, result, 1800)
            return result
        
        # Contexto formatado
        context = self._prepare_context(search_results, max_length=800)
        
        # Contexto do usuário para personalização
        user_context = {
            'name': getattr(user, 'name', 'Colaborador') if user else 'Colaborador',
            'department': analysis.get('personalization', {}).get('department'),
            'role': analysis.get('personalization', {}).get('role')
        }
        
        # Prompt simplificado para Knight
        user_name = user_context.get('name', 'usuário')
        prompt = f"""Você é o Knight ⚔️, assistente de RH especializado em políticas e processos corporativos.

Query do usuário: {query}

Contexto disponível:
{context}

Instruções:
- Responda de forma clara e profissional para {user_name}
- Use as informações do contexto quando relevantes
- Se não tiver informações suficientes, seja direto sobre isso
- Foque em ajudar com questões de RH e processos internos"""
        
        # Parâmetros dinâmicos baseados no contexto
        temperature = 0.5 if analysis.get('complexity_score', 0.5) < 0.4 else 0.7
        max_tokens = 400 if analysis.get('urgency_level') == 'high' else 600
        
        llm_response = self.llm_manager.generate_response(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        response_text = llm_response.get("response", "Desculpe, tive um problema técnico. Pode tentar reformular sua pergunta?")
        
        # Resposta final simplificada  
        result = {
            "response": response_text,
            "search_results": search_results,
            "agent_used": "knight",
            "metadata": {
                "provider_used": llm_response.get("provider", "unknown"),
                "agent_used": "knight",
                "task_type": "general_hr"
            }
        }
        
        # Cache simples
        cache.set(cache_key, result, 1800)
        
        return result
    
    def _bard_fast_response(self, query: str, user_profile: Dict, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Bard - Central de Relatórios e Análises de Performance"""
        import logging
        
        logger = logging.getLogger(__name__)
        user_name = user_profile.get('name', 'Colaborador')
        user_role = user_profile.get('role', 'colaborador')
        
        try:
            # Buscar dados relevantes para análise
            search_results = self.vector_search.search(query, k=5)
            
            # Determinar escopo de análise baseado no role do usuário
            if user_role == 'admin' or user_role == 'administrator':
                scope = "todos os colaboradores e métricas organizacionais"
                access_level = "completo"
            else:
                scope = "suas métricas e performance pessoal"
                access_level = "pessoal"
            
            # Contexto formatado com foco em análise
            context = self._prepare_context(search_results[:4]) if search_results else "Nenhum dado específico encontrado."
            
            # Prompt analítico genérico
            prompt = f"""Você é o Bard 🎭, Central de Relatórios e Análises de Performance.

**Usuário**: {user_name} ({user_role})
**Consulta**: {query}
**Escopo de análise**: {scope}
**Nível de acesso**: {access_level}

**Contexto disponível**:
{context}

**Instruções**:
- Como Central de Análises, forneça insights baseados nos dados disponíveis
- Para administradores: análises organizacionais completas
- Para colaboradores: foco em métricas pessoais e de equipe
- Se não houver dados específicos, sugira métricas relevantes para coleta
- Use visualizações quando apropriado (gráficos, tabelas, dashboards)
- Seja analítico, objetivo e orientado a dados

**Formato de resposta**: Análise estruturada com insights acionáveis"""
            
            # Gerar resposta com tratamento de erro robusto
            try:
                llm_response = self.llm_manager.generate_response(
                    prompt=prompt,
                    max_tokens=600,
                    temperature=0.7
                )
                
                if llm_response.get("success", False):
                    response_text = llm_response.get("response", "")
                    provider_used = llm_response.get("provider", "unknown")
                else:
                    logger.error(f"LLM failed for Bard: {llm_response.get('error', 'Unknown error')}")
                    response_text = self._get_bard_generic_fallback(query, user_name, scope)
                    provider_used = "fallback"
                    
            except Exception as llm_error:
                logger.error(f"Exception in LLM for Bard: {str(llm_error)}")
                response_text = self._get_bard_generic_fallback(query, user_name, scope)
                provider_used = "fallback_exception"
            
            return {
                "response": response_text,
                "search_results": search_results,
                "metadata": {
                    "provider_used": provider_used,
                    "agent_used": "bard",
                    "task_type": "analytical",
                    "scope": scope,
                    "access_level": access_level
                },
                "agent_used": "bard"
            }
            
        except Exception as e:
            logger.error(f"Critical error in _bard_fast_response: {str(e)}")
            return {
                "response": f"🎭 Olá {user_name}! Sou o Bard, Central de Análises. Tive uma dificuldade técnica, mas posso ajudar com qualquer análise ou relatório. Pode reformular sua consulta?",
                "search_results": [],
                "metadata": {"provider_used": "error_fallback", "agent_used": "bard", "error": str(e)},
                "agent_used": "bard"
            }
    
    def _wizard_fast_response(self, query: str, user_profile: Dict, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Wizard - Especialista em capacitação e desenvolvimento (versão simplificada)"""
        
        # Busca por conteúdos de capacitação
        search_results = self.vector_search.search(query, k=3)
        context = self._prepare_context(search_results)
        
        # Contexto do usuário para personalização
        user_name = user_profile.get('name', 'Colaborador')
        user_role = user_profile.get('role', 'sua função')
        
        # Prompt direto para capacitação
        prompt = f"""Você é o Wizard 🧙, especialista em capacitação e desenvolvimento profissional.

Query do usuário: {query}

Contexto disponível:
{context}

Instruções:
- Ajude {user_name} com orientações práticas sobre treinamentos e desenvolvimento
- Seja motivador e ofereça sugestões concretas
- Foque em capacitação para {user_role}
- Se não houver informações suficientes, sugira onde encontrar recursos"""
        
        # Gerar resposta
        llm_response = self.llm_manager.generate_response(
            prompt=prompt,
            max_tokens=400,
            temperature=0.8
        )
        
        response_text = llm_response.get("response", f"🧙 Olá {user_name}! Preciso de mais detalhes sobre o que você gostaria de aprender. Pode me dar mais contexto?")
        
        return {
            "response": response_text,
            "search_results": search_results,
            "metadata": {
                "provider_used": llm_response.get("provider", "unknown"),
                "agent_used": "wizard",
                "task_type": "training"
            },
            "agent_used": "wizard"
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
    
    def _get_fallback_response(self, query: str, force_mode: Optional[str], start_time: float) -> Dict[str, Any]:
        """Resposta de fallback quando serviços não estão disponíveis"""
        
        if force_mode == 'wizard':
            response = "🧙 Olá! Sou o Wizard, especialista em capacitação.\n\nPosso ajudar com:\n• Cursos e treinamentos\n• Desenvolvimento profissional\n• Certificações\n• Planos de carreira\n\nComo posso ajudar no seu desenvolvimento?"
            agent = 'wizard'
        elif force_mode == 'bard':
            response = "🎭 Olá! Sou o Bard, especialista em análises.\n\nPosso ajudar com:\n• Análise de dados\n• Relatórios e dashboards\n• Métricas e KPIs\n• Insights de performance\n\nQue tipo de análise você precisa?"
            agent = 'bard'
        else:
            response = "⚔️ Olá! Sou o Knight, seu assistente de RH.\n\nEstou com limitações técnicas no momento, mas posso tentar ajudar. Como posso auxiliar você?"
            agent = 'knight'
        
        return {
            "query": query,
            "response": response,
            "agent_used": agent,
            "execution_path": ["fallback"],
            "search_results": [],
            "metadata": {
                "provider_used": "fallback",
                "error": "Services not initialized",
                "total_duration_ms": int((time.time() - start_time) * 1000)
            },
            "useful_links": [],
            "downloadable_documents": []
        }
    
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
            },
            "useful_links": [],
            "downloadable_documents": []
        }
    
    def _extract_action_suggestions(self, context: str) -> List[str]:
        """Extrai sugestões de ações do contexto"""
        actions = []
        action_patterns = [
            r'deve\s+(\w+)',
            r'recomenda-se\s+(\w+)',
            r'é\s+necessário\s+(\w+)',
            r'procure\s+(\w+)',
            r'contate\s+(\w+)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, context.lower())
            actions.extend(matches[:2])  # Max 2 por padrão
            
        return actions[:3]  # Max 3 ações total
    
    def _extract_contact_info(self, context: str) -> List[str]:
        """Extrai informações de contato do contexto"""
        contacts = []
        contact_patterns = [
            r'RH',
            r'Recursos\s+Humanos',
            r'gerente',
            r'supervisor',
            r'departamento',
            r'setor'
        ]
        
        for pattern in contact_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                contacts.append(pattern.replace(r'\s+', ' '))
                
        return contacts[:2]  # Max 2 contatos
    
    def _prepare_analytical_context(self, search_results: List[Dict], max_length: int = 900) -> str:
        """Prepara contexto focado em dados e análises"""
        if not search_results:
            return ""
        
        # Priorizar documentos com dados, números, métricas
        analytical_results = []
        for result in search_results:
            content = result.get('content', '')
            # Boost para conteúdo com números e dados
            if re.search(r'\d+[%]|\d+\.\d+|métrica|indicador|performance', content, re.IGNORECASE):
                analytical_results.insert(0, result)
            else:
                analytical_results.append(result)
        
        # Formatar contexto analítico
        formatted_parts = []
        current_length = 0
        
        for i, result in enumerate(analytical_results[:4]):
            content = result.get('content', '')[:300]
            formatted_content = f"FONTE {i+1}: {content}"
            
            if current_length + len(formatted_content) <= max_length:
                formatted_parts.append(formatted_content)
                current_length += len(formatted_content)
            else:
                break
                
        return "\n\n".join(formatted_parts)
    
    def _extract_analytical_actions(self, context: str) -> List[str]:
        """Extrai ações analíticas do contexto"""
        actions = []
        analytical_patterns = [
            'analisar dados',
            'gerar relatório',
            'comparar métricas',
            'acompanhar indicadores',
            'criar dashboard'
        ]
        
        for pattern in analytical_patterns:
            if pattern.split()[0] in context.lower():
                actions.append(pattern)
                
        return actions[:3]
    
    def _extract_visualization_opportunities(self, context: str) -> List[str]:
        """Identifica oportunidades de visualização de dados"""
        viz_hints = []
        
        if re.search(r'comparar|versus|tendência', context, re.IGNORECASE):
            viz_hints.append("gráfico de linha ou barras")
            
        if re.search(r'distribuição|percentual|proporção', context, re.IGNORECASE):
            viz_hints.append("gráfico de pizza ou donut")
            
        if re.search(r'evolução|tempo|histórico', context, re.IGNORECASE):
            viz_hints.append("série temporal")
            
        return viz_hints[:2]
    
    def _get_bard_generic_fallback(self, query: str, user_name: str, scope: str) -> str:
        """Resposta de fallback genérica quando LLM falha"""
        return f"""🎭 Olá {user_name}! 

Sou o Bard, sua Central de Análises. Tive uma dificuldade técnica, mas estou aqui para ajudar com qualquer análise sobre {scope}.

Sobre "{query}", posso te auxiliar das seguintes formas:

📊 **Posso analisar:**
• Dados e planilhas que você compartilhar
• Métricas específicas que você mencionar  
• Relatórios que precisam de interpretação
• Indicadores de performance e tendências

💡 **Dica:** Seja mais específico sobre quais dados, métricas ou análises você precisa, e eu conseguirei te dar uma resposta mais precisa!

🎭 Para análises interativas completas, visite também [Central de Relatórios](/bard)"""

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
                "simplified_cache": True,
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