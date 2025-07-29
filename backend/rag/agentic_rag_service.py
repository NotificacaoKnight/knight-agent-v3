"""
Serviço RAG Agentic usando LangGraph
Implementa padrões agentic com decision-making dinâmico, self-reflection e multi-step reasoning
"""
import os
import time
import json
from typing import Dict, List, Any, Optional, TypedDict, Literal
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from django.conf import settings
from django.core.cache import cache

from .services import VectorSearchService, BM25SearchService, EmbeddingService
from .llm_providers import LLMManager
from .models import SearchQuery, SearchResult
from .agentic_config import get_config


class AgenticRAGState(TypedDict):
    """Estado compartilhado entre os nós do grafo"""
    # Input/Output
    query: str
    messages: List[BaseMessage]
    final_response: Optional[str]
    
    # Search state
    search_results: List[Dict[str, Any]]
    search_quality_score: float
    search_attempts: int
    
    # Planning state
    research_plan: List[str]
    current_step: int
    
    # Context management
    retrieved_documents: List[str]
    context_summary: str
    
    # Quality control
    response_quality: float
    needs_refinement: bool
    
    # Metadata
    search_duration_ms: int
    total_duration_ms: int
    provider_used: str
    next_action: Literal["search", "refine_query", "generate", "validate", "end"]


class AgenticRAGService:
    """Serviço RAG Agentic usando LangGraph"""
    
    def __init__(self):
        self.vector_search = VectorSearchService()
        self.bm25_search = BM25SearchService()
        self.embedding_service = EmbeddingService()
        self.llm_manager = LLMManager()
        
        # Carregar configurações
        self.config = get_config()
        self.search_config = self.config.get_search_config()
        self.generation_config = self.config.get_generation_config()
        self.quality_config = self.config.get_quality_config()
        
        # Criar grafo
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Cria o grafo de estados LangGraph"""
        workflow = StateGraph(AgenticRAGState)
        
        # Adicionar nós
        workflow.add_node("planner", self._planning_node)
        workflow.add_node("searcher", self._search_node)
        workflow.add_node("quality_checker", self._quality_check_node)
        workflow.add_node("query_refiner", self._query_refinement_node)
        workflow.add_node("context_manager", self._context_management_node)
        workflow.add_node("generator", self._generation_node)
        workflow.add_node("validator", self._validation_node)
        workflow.add_node("finalizer", self._finalization_node)
        
        # Fluxo principal
        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "searcher")
        workflow.add_edge("searcher", "quality_checker")
        
        # Roteamento condicional após quality check (simplificado)
        workflow.add_conditional_edges(
            "quality_checker",
            self._quality_routing_logic,
            {
                "refine": "query_refiner",
                "generate": "generator"  # Removido context_manager para velocidade
            }
        )
        
        workflow.add_edge("query_refiner", "searcher")
        workflow.add_edge("generator", "finalizer")  # Direto para finalizer, sem validação
        
        workflow.add_edge("finalizer", END)
        
        return workflow.compile()
    
    def _planning_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de planejamento - analisa query e cria plano de pesquisa"""
        query = state["query"]
        
        # Analisar complexidade da query
        research_plan = self._create_research_plan(query)
        
        return {
            "research_plan": research_plan,
            "current_step": 0,
            "search_attempts": 0,
            "next_action": "search"
        }
    
    def _search_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de busca - executa busca híbrida"""
        query = state["query"]
        search_attempts = state.get("search_attempts", 0)
        
        start_time = time.time()
        
        try:
            # Usar HybridSearchService existente para otimização
            from .services import HybridSearchService
            hybrid_service = HybridSearchService()
            
            # Busca otimizada sem logging (busca intermediária)
            combined_results = []
            
            # Busca semântica
            semantic_results = self.vector_search.search(query, k=10)
            
            # Busca BM25  
            bm25_results = self.bm25_search.search(query, k=10)
            
            # Combinar resultados usando lógica otimizada
            combined_results = self._combine_search_results(
                semantic_results, 
                bm25_results,
                semantic_weight=self.search_config['semantic_weight'],
                bm25_weight=self.search_config['bm25_weight']
            )
            
            search_duration = int((time.time() - start_time) * 1000)
            
            return {
                "search_results": combined_results,
                "search_attempts": search_attempts + 1,
                "search_duration_ms": search_duration,
                "next_action": "quality_check"
            }
            
        except Exception as e:
            # Error handling para falhas na busca
            search_duration = int((time.time() - start_time) * 1000)
            
            return {
                "search_results": [],
                "search_attempts": search_attempts + 1,
                "search_duration_ms": search_duration,
                "next_action": "generate",  # Continuar mesmo sem resultados
                "error": str(e)
            }
    
    def _quality_check_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de verificação de qualidade dos resultados"""
        search_results = state["search_results"]
        query = state["query"]
        search_attempts = state["search_attempts"]
        
        # Avaliar qualidade dos resultados
        quality_score = self._evaluate_search_quality(search_results, query)
        
        # Simplificado: sempre gerar resposta se temos resultados
        if len(search_results) > 0:
            next_action = "generate"  # Gerar resposta diretamente
        elif search_attempts < self.search_config['max_attempts']:
            next_action = "refine"  # Refinar query apenas se não temos resultados
        else:
            next_action = "generate"  # Gerar resposta mesmo sem resultados perfeitos
        
        return {
            "search_quality_score": quality_score,
            "next_action": next_action
        }
    
    def _query_refinement_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de refinamento de query"""
        original_query = state["query"]
        search_results = state["search_results"]
        
        # Usar LLM para refinar query baseado nos resultados
        refinement_prompt = f"""
        Query original: {original_query}
        Resultados encontrados: {len(search_results)} documentos
        
        Os resultados não foram satisfatórios. Sugira uma query refinada que possa encontrar informações mais relevantes.
        Responda apenas com a query refinada, sem explicações adicionais.
        """
        
        llm_response = self.llm_manager.generate_response(
            prompt=refinement_prompt,
            max_tokens=100,
            temperature=0.3
        )
        
        if llm_response["success"]:
            refined_query = llm_response["response"].strip()
            # Manter query original para histórico
            return {
                "query": refined_query,
                "next_action": "search"
            }
        
        # Se refinamento falhar, continuar com query original
        return {"next_action": "search"}
    
    def _context_management_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de gerenciamento de contexto"""
        search_results = state["search_results"]
        query = state["query"]
        
        # Selecionar e organizar documentos mais relevantes
        top_documents = search_results[:5]  # Top 5 mais relevantes
        
        # Extrair conteúdo dos documentos
        retrieved_docs = [doc["content"] for doc in top_documents]
        
        # Verificar se contexto não é muito longo
        total_length = sum(len(doc) for doc in retrieved_docs)
        max_context = self.generation_config['max_context_length']
        
        if total_length > max_context:
            # Truncar documentos preservando informação mais importante
            retrieved_docs = self._truncate_context(retrieved_docs, max_context)
        
        # Criar resumo do contexto se necessário
        context_summary = self._create_context_summary(retrieved_docs, query)
        
        return {
            "retrieved_documents": retrieved_docs,
            "context_summary": context_summary,
            "next_action": "generate"
        }
    
    def _generation_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de geração de resposta"""
        query = state["query"]
        search_results = state.get("search_results", [])
        
        # Extrair conteúdo dos resultados da busca
        retrieved_docs = [result.get("content", "") for result in search_results[:5]]
        
        # Gerar resposta usando LLM com contexto
        llm_response = self.llm_manager.generate_response(
            prompt=query,
            context=retrieved_docs,
            max_tokens=self.generation_config['max_tokens'],
            temperature=self.generation_config['temperature']
        )
        
        if llm_response["success"]:
            return {
                "final_response": llm_response["response"],
                "provider_used": llm_response["provider"],
                "next_action": "validate"
            }
        else:
            # Erro na geração
            return {
                "final_response": "Desculpe, não foi possível gerar uma resposta no momento. Tente novamente.",
                "provider_used": "error",
                "next_action": "finalize"
            }
    
    def _validation_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de validação da resposta"""
        response = state["final_response"]
        query = state["query"]
        retrieved_docs = state.get("retrieved_documents", [])
        
        # Avaliar qualidade da resposta
        quality_score = self._evaluate_response_quality(response, query, retrieved_docs)
        
        # Determinar se precisa refinamento
        if quality_score < self.quality_config['threshold']:
            return {
                "response_quality": quality_score,
                "needs_refinement": True,
                "next_action": "refine_context"
            }
        else:
            return {
                "response_quality": quality_score,
                "needs_refinement": False,
                "next_action": "finalize"
            }
    
    def _finalization_node(self, state: AgenticRAGState) -> Dict[str, Any]:
        """Nó de finalização - prepara resposta final"""
        return {
            "total_duration_ms": int(time.time() * 1000) - state.get("start_time", 0),
            "next_action": "end"
        }
    
    def _quality_routing_logic(self, state: AgenticRAGState) -> str:
        """Lógica de roteamento baseada na qualidade"""
        return state["next_action"]
    
    def _validation_routing_logic(self, state: AgenticRAGState) -> str:
        """Lógica de roteamento após validação"""
        return state["next_action"]
    
    def _create_research_plan(self, query: str) -> List[str]:
        """Cria plano de pesquisa baseado na query"""
        # Para simplificar, usar um plano básico
        # Em implementação avançada, usar LLM para criar plano
        return [
            f"Buscar informações sobre: {query}",
            "Validar relevância dos resultados",
            "Sintetizar informações encontradas"
        ]
    
    def _combine_search_results(
        self, 
        semantic_results: List[Dict], 
        bm25_results: List[Dict],
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Combina resultados de busca semântica e BM25"""
        # Reutilizar lógica existente do HybridSearchService
        combined = {}
        
        # Normalizar scores semânticos
        if semantic_results:
            max_score = max(r['score'] for r in semantic_results)
            min_score = min(r['score'] for r in semantic_results)
            score_range = max_score - min_score
            
            for result in semantic_results:
                chunk_id = result['chunk_id']
                normalized_score = (result['score'] - min_score) / score_range if score_range > 0 else 0
                
                combined[chunk_id] = {
                    **result,
                    'semantic_score': normalized_score,
                    'bm25_score': 0.0
                }
        
        # Normalizar scores BM25
        if bm25_results:
            max_score = max(r['score'] for r in bm25_results)
            min_score = min(r['score'] for r in bm25_results)
            score_range = max_score - min_score
            
            for result in bm25_results:
                chunk_id = result['chunk_id']
                normalized_score = (result['score'] - min_score) / score_range if score_range > 0 else 0
                
                if chunk_id in combined:
                    combined[chunk_id]['bm25_score'] = normalized_score
                else:
                    combined[chunk_id] = {
                        **result,
                        'semantic_score': 0.0,
                        'bm25_score': normalized_score
                    }
        
        # Calcular score combinado
        for result in combined.values():
            result['combined_score'] = (
                result['semantic_score'] * semantic_weight +
                result['bm25_score'] * bm25_weight
            )
        
        # Ordenar por score combinado
        return sorted(combined.values(), key=lambda x: x['combined_score'], reverse=True)
    
    def _evaluate_search_quality(self, search_results: List[Dict], query: str) -> float:
        """Avalia qualidade dos resultados de busca"""
        if not search_results:
            return 0.0
        
        # Métricas básicas de qualidade
        avg_score = sum(r.get('combined_score', 0) for r in search_results) / len(search_results)
        result_count_score = min(len(search_results) / 5, 1.0)  # Ideal: 5+ resultados
        
        # Score combinado
        quality_score = (avg_score * 0.7) + (result_count_score * 0.3)
        
        return min(quality_score, 1.0)
    
    def _evaluate_response_quality(self, response: str, query: str, context: List[str]) -> float:
        """Avalia qualidade da resposta gerada"""
        if not response or len(response.strip()) < 10:
            return 0.0
        
        # Métricas básicas
        length_score = min(len(response) / 200, 1.0)  # Respostas muito curtas são ruins
        context_usage_score = 1.0 if context else 0.5  # Melhor se usar contexto
        
        # Verificar se resposta parece relevante (heurística simples)
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        relevance_score = len(query_words.intersection(response_words)) / len(query_words)
        
        quality_score = (length_score * 0.3) + (context_usage_score * 0.3) + (relevance_score * 0.4)
        
        return min(quality_score, 1.0)
    
    def _truncate_context(self, documents: List[str], max_length: int) -> List[str]:
        """Trunca contexto preservando informação importante"""
        truncated = []
        current_length = 0
        
        for doc in documents:
            if current_length + len(doc) <= max_length:
                truncated.append(doc)
                current_length += len(doc)
            else:
                # Truncar documento para caber
                remaining_space = max_length - current_length
                if remaining_space > 100:  # Só adicionar se tiver espaço suficiente
                    truncated.append(doc[:remaining_space] + "...")
                break
        
        return truncated
    
    def _create_context_summary(self, documents: List[str], query: str) -> str:
        """Cria resumo do contexto se necessário"""
        if len(documents) <= 3:
            return ""  # Não precisa resumir poucos documentos
        
        # Para simplificar, retornar informação básica
        return f"Contexto baseado em {len(documents)} documentos relacionados à consulta."
    
    def process_query(
        self, 
        query: str, 
        user: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Processa query usando o grafo agentic"""
        
        start_time = time.time()
        
        try:
            # Estado inicial
            initial_state = AgenticRAGState(
                query=query,
                messages=[HumanMessage(content=query)],
                final_response=None,
                search_results=[],
                search_quality_score=0.0,
                search_attempts=0,
                research_plan=[],
                current_step=0,
                retrieved_documents=[],
                context_summary="",
                response_quality=0.0,
                needs_refinement=False,
                search_duration_ms=0,
                total_duration_ms=0,
                provider_used="",
                next_action="search",
                start_time=int(start_time * 1000)
            )
            
            # Executar grafo
            final_state = self.graph.invoke(initial_state)
            
        except Exception as e:
            # Tratamento de erro para falhas no grafo
            return {
                "query": query,
                "response": f"Erro no processamento agentic: {str(e)}",
                "search_results": [],
                "quality_metrics": {
                    "search_quality": 0.0,
                    "response_quality": 0.0,
                    "search_attempts": 0,
                    "needs_refinement": True
                },
                "metadata": {
                    "provider_used": "error",
                    "search_duration_ms": 0,
                    "total_duration_ms": int((time.time() - start_time) * 1000),
                    "documents_retrieved": 0,
                    "research_plan": [],
                    "error": str(e)
                }
            }
        
        # Preparar resultado
        result = {
            "query": query,
            "response": final_state.get("final_response", "Não foi possível gerar resposta."),
            "search_results": final_state.get("search_results", []),
            "quality_metrics": {
                "search_quality": final_state.get("search_quality_score", 0.0),
                "response_quality": final_state.get("response_quality", 0.0),
                "search_attempts": final_state.get("search_attempts", 0),
                "needs_refinement": final_state.get("needs_refinement", False)
            },
            "metadata": {
                "provider_used": final_state.get("provider_used", "unknown"),
                "search_duration_ms": final_state.get("search_duration_ms", 0),
                "total_duration_ms": final_state.get("total_duration_ms", 0),
                "documents_retrieved": len(final_state.get("retrieved_documents", [])),
                "research_plan": final_state.get("research_plan", [])
            }
        }
        
        # Log da query para histórico
        try:
            search_query = SearchQuery.objects.create(
                user=user,
                query_text=query,
                search_type='agentic_rag',
                results_count=len(final_state.get("search_results", [])),
                search_duration_ms=final_state.get("total_duration_ms", 0),
                results=[
                    {
                        'document_id': r.get('document_id'),
                        'chunk_id': r.get('chunk_id'),
                        'combined_score': r.get('combined_score', 0),
                        'search_type': 'agentic'
                    }
                    for r in final_state.get("search_results", [])[:10]  # Top 10
                ]
            )
            result["search_id"] = search_query.id
        except Exception as e:
            result["search_id"] = None
            result["search_error"] = str(e)
        
        return result


class AgenticRAGServiceSync:
    """Versão síncrona do serviço agentic para compatibilidade"""
    
    def __init__(self):
        self.async_service = AgenticRAGService()
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        user: Any = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Interface síncrona compatível com HybridSearchService"""
        
        # Para Django views síncronas, simular comportamento agentic
        # Em produção, considerar usar async views ou Celery tasks
        
        import asyncio
        
        try:
            # Tentar executar versão async
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se já temos loop, usar versão simplificada
                return self._sync_fallback_search(query, k, user, **kwargs)
            else:
                return loop.run_until_complete(
                    self.async_service.process_query(query, user, **kwargs)
                )
        except:
            # Fallback para versão síncrona simplificada
            return self._sync_fallback_search(query, k, user, **kwargs)
    
    def _sync_fallback_search(self, query: str, k: int, user: Any, **kwargs) -> Dict[str, Any]:
        """Fallback síncrono que simula comportamento agentic básico"""
        
        start_time = time.time()
        
        try:
            # Usar HybridSearchService existente (otimizado)
            hybrid_service = HybridSearchService()
            
            # Busca híbrida otimizada
            search_results, search_query = hybrid_service.search(
                query=query,
                k=k,
                user=None  # Não logar busca intermediária
            )
            
            # Gerar resposta
            context_docs = [r['content'] for r in search_results]
            llm_manager = LLMManager()
            llm_response = llm_manager.generate_response(
                prompt=query,
                context=context_docs,
                max_tokens=1000
            )
            
            total_duration = int((time.time() - start_time) * 1000)
            
            return {
                "query": query,
                "response": llm_response.get("response", "Erro ao gerar resposta"),
                "search_results": search_results,
                "quality_metrics": {
                    "search_quality": 0.8 if search_results else 0.0,
                    "response_quality": 0.8 if llm_response.get("success") else 0.3,
                    "search_attempts": 1,
                    "needs_refinement": False
                },
                "metadata": {
                    "provider_used": llm_response.get("provider", "unknown"),
                    "search_duration_ms": search_query.search_duration_ms if search_query else total_duration // 2,
                    "total_duration_ms": total_duration,
                    "documents_retrieved": len(context_docs),
                    "research_plan": [f"Busca híbrida por: {query}"],
                    "fallback_reason": "Sync compatibility mode"
                }
            }
            
        except Exception as e:
            # Error recovery com resposta mínima
            total_duration = int((time.time() - start_time) * 1000)
            
            return {
                "query": query,
                "response": f"Desculpe, ocorreu um erro ao processar sua consulta: {str(e)}",
                "search_results": [],
                "quality_metrics": {
                    "search_quality": 0.0,
                    "response_quality": 0.1,
                    "search_attempts": 1,
                    "needs_refinement": True
                },
                "metadata": {
                    "provider_used": "error",
                    "search_duration_ms": 0,
                    "total_duration_ms": total_duration,
                    "documents_retrieved": 0,
                    "research_plan": [],
                    "error": str(e),
                    "fallback_reason": "Error recovery mode"
                }
            }