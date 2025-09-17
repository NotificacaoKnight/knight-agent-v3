"""
Consolidated Multi-Agent Service - Single system with automatic adaptation
Combines all functionalities:
- Knight: General supervisor agent
- Bard: Report generation specialist
- Wizard: Training and documentation specialist
"""
import time
import re
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime

try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None

from app.services.rag.hybrid_search_service import get_hybrid_search_service
from app.services.rag.bm25_service import BM25SearchService
from app.services.rag.llm_providers import llm_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiAgentState(TypedDict):
    """Shared state between all agents"""
    query: str
    user_profile: Dict[str, Any]
    agent_used: str
    search_results: List[Dict]
    response: str
    metadata: Dict[str, Any]
    execution_path: List[str]
    quality_score: float
    processing_mode: str  # 'fast' or 'complete'
    chat_history: List[Dict[str, Any]]
    user_language: str


class ConsolidatedMultiAgentService:
    """Unified multi-agent system with automatic adaptation"""

    def __init__(self):
        # Core services
        self.vector_search = get_hybrid_search_service()
        self.bm25_search = BM25SearchService()
        self.llm_manager = llm_manager

        # Build complex graph if LangGraph available
        self.complex_graph = self._build_complex_graph() if HAS_LANGGRAPH else None

        # Cache for intent analysis
        self._intent_cache = {}

        logger.info("ConsolidatedMultiAgentService initialized successfully")

    async def process_query(
        self,
        query: str,
        user_profile: Dict[str, Any] = None,
        force_mode: Optional[str] = None,
        chat_history: List[Dict[str, Any]] = None,
        user_language: str = "pt",
        **kwargs
    ) -> Dict[str, Any]:
        """Main entry point - automatically decides between fast/complete"""

        start_time = time.time()
        user_profile = user_profile or {}

        # Check cache
        cache_key = self._generate_cache_key(query)
        cached_result = self._check_cache(cache_key)
        if cached_result:
            return cached_result

        # Analyze query complexity
        complexity = self._analyze_complexity(query)
        agent = self._determine_agent(query, complexity)

        # Decide processing mode
        if force_mode:
            mode = force_mode
        elif complexity > 0.7:
            mode = "complete"
        else:
            mode = "fast"

        logger.info(f"Processing query with {agent} agent in {mode} mode")

        # Execute appropriate processing
        if mode == "complete" and self.complex_graph:
            result = await self._execute_complete_mode(
                query, agent, user_profile, chat_history, user_language
            )
        else:
            result = await self._execute_fast_mode(
                query, agent, user_profile, user_language
            )

        # Add metadata
        result["metadata"].update({
            "processing_mode": mode,
            "complexity_score": complexity,
            "agent_used": agent,
            "total_time_ms": int((time.time() - start_time) * 1000)
        })

        # Cache result
        self._save_to_cache(cache_key, result)

        return result

    def _analyze_complexity(self, query: str) -> float:
        """Analyzes query complexity (0-1)"""
        score = 0.0

        # Length factor
        if len(query) > 100:
            score += 0.2

        # Keywords indicating complexity
        complex_keywords = [
            "comparar", "analisar", "explicar detalhadamente",
            "passo a passo", "treinar", "documentar",
            "relatório", "análise completa", "estratégia"
        ]

        for keyword in complex_keywords:
            if keyword.lower() in query.lower():
                score += 0.15

        # Question words
        question_words = ["como", "por que", "quando", "onde", "quem"]
        for word in question_words:
            if word in query.lower():
                score += 0.1

        return min(score, 1.0)

    def _determine_agent(self, query: str, complexity: float) -> str:
        """Determines which agent to use"""
        query_lower = query.lower()

        # Bard: Reports and documentation
        if any(word in query_lower for word in ["relatório", "documentação", "análise detalhada", "report"]):
            return "bard"

        # Wizard: Training and tutorials
        if any(word in query_lower for word in ["treinar", "tutorial", "passo a passo", "ensinar", "aprender"]):
            return "wizard"

        # Knight: General supervisor (default)
        return "knight"

    def _build_complex_graph(self) -> Optional[StateGraph]:
        """Builds the LangGraph state machine for complex queries"""
        if not HAS_LANGGRAPH:
            return None

        workflow = StateGraph(MultiAgentState)

        # Add nodes for each agent
        workflow.add_node("knight_analysis", self._knight_analysis_node)
        workflow.add_node("bard_generation", self._bard_generation_node)
        workflow.add_node("wizard_training", self._wizard_training_node)
        workflow.add_node("search", self._search_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Define flow
        workflow.add_edge(START, "knight_analysis")
        workflow.add_conditional_edges(
            "knight_analysis",
            self._route_to_agent,
            {
                "bard": "bard_generation",
                "wizard": "wizard_training",
                "search": "search"
            }
        )

        workflow.add_edge("bard_generation", "search")
        workflow.add_edge("wizard_training", "search")
        workflow.add_edge("search", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    async def _knight_analysis_node(self, state: MultiAgentState) -> MultiAgentState:
        """Knight supervisor agent - analyzes and routes"""
        state["execution_path"].append("knight_analysis")
        state["agent_used"] = state.get("agent_used", "knight")
        return state

    async def _bard_generation_node(self, state: MultiAgentState) -> MultiAgentState:
        """Bard agent - specializes in report generation"""
        state["execution_path"].append("bard_generation")
        state["metadata"]["report_mode"] = True
        return state

    async def _wizard_training_node(self, state: MultiAgentState) -> MultiAgentState:
        """Wizard agent - specializes in training and documentation"""
        state["execution_path"].append("wizard_training")
        state["metadata"]["training_mode"] = True
        return state

    async def _search_node(self, state: MultiAgentState) -> MultiAgentState:
        """Executes search"""
        try:
            results = await self.vector_search.search(
                query=state["query"],
                k=10,
                search_type="hybrid"
            )
            state["search_results"] = results
        except Exception as e:
            logger.error(f"Search error: {e}")
            state["search_results"] = []

        state["execution_path"].append("search")
        return state

    async def _generate_response_node(self, state: MultiAgentState) -> MultiAgentState:
        """Generates final response"""
        try:
            context = self._build_context(state["search_results"])
            prompt = self._build_prompt(state)

            response, provider = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                context=context,
                max_tokens=1000,
                temperature=0.7
            )

            state["response"] = response
            state["metadata"]["llm_provider"] = str(provider)

        except Exception as e:
            logger.error(f"Generation error: {e}")
            state["response"] = self._get_error_message(state["user_language"])

        state["execution_path"].append("generate_response")
        return state

    def _route_to_agent(self, state: MultiAgentState) -> str:
        """Routes to specific agent based on analysis"""
        agent = state.get("agent_used", "knight")

        if agent == "bard":
            return "bard"
        elif agent == "wizard":
            return "wizard"
        else:
            return "search"

    async def _execute_complete_mode(
        self,
        query: str,
        agent: str,
        user_profile: Dict,
        chat_history: List[Dict],
        user_language: str
    ) -> Dict[str, Any]:
        """Executes in complete mode with LangGraph"""
        if not self.complex_graph:
            return await self._execute_fast_mode(query, agent, user_profile, user_language)

        try:
            # Initialize state
            initial_state = MultiAgentState(
                query=query,
                user_profile=user_profile,
                agent_used=agent,
                search_results=[],
                response="",
                metadata={},
                execution_path=[],
                quality_score=0.0,
                processing_mode="complete",
                chat_history=chat_history or [],
                user_language=user_language
            )

            # Execute graph
            result = await self.complex_graph.ainvoke(initial_state)

            return {
                "success": True,
                "response": result["response"],
                "agent": result["agent_used"],
                "sources": result["search_results"][:5],
                "metadata": result["metadata"],
                "execution_path": result["execution_path"]
            }

        except Exception as e:
            logger.error(f"Complete mode error: {e}")
            return await self._execute_fast_mode(query, agent, user_profile, user_language)

    async def _execute_fast_mode(
        self,
        query: str,
        agent: str,
        user_profile: Dict,
        user_language: str
    ) -> Dict[str, Any]:
        """Executes in fast mode without LangGraph"""
        try:
            # Quick search
            search_results = await self.vector_search.search(
                query=query,
                k=5,
                search_type="hybrid"
            )

            # Build context and generate response
            context = self._build_context(search_results)
            prompt = self._build_simple_prompt(query, agent, user_language)

            response, provider = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                context=context,
                max_tokens=800,
                temperature=0.7
            )

            return {
                "success": True,
                "response": response,
                "agent": agent,
                "sources": search_results[:3],
                "metadata": {
                    "mode": "fast",
                    "llm_provider": str(provider)
                }
            }

        except Exception as e:
            logger.error(f"Fast mode error: {e}")
            return {
                "success": False,
                "response": self._get_error_message(user_language),
                "agent": agent,
                "error": str(e),
                "metadata": {"mode": "fast"}
            }

    def _build_context(self, search_results: List[Dict]) -> str:
        """Builds context from search results"""
        if not search_results:
            return ""

        context_parts = []
        for i, result in enumerate(search_results[:5], 1):
            content = result.get("content", "")
            context_parts.append(f"[{i}] {content}")

        return "\n\n".join(context_parts)

    def _build_prompt(self, state: MultiAgentState) -> str:
        """Builds complex prompt based on agent and state"""
        agent = state["agent_used"]
        query = state["query"]
        language = state["user_language"]

        if agent == "bard":
            if language == "pt":
                return f"""
                Como especialista em relatórios, crie uma análise detalhada para:
                {query}

                Estruture a resposta com:
                1. Resumo executivo
                2. Análise detalhada
                3. Conclusões e recomendações
                """
            else:
                return f"""
                As a reporting specialist, create a detailed analysis for:
                {query}

                Structure the response with:
                1. Executive summary
                2. Detailed analysis
                3. Conclusions and recommendations
                """

        elif agent == "wizard":
            if language == "pt":
                return f"""
                Como especialista em treinamento, crie um tutorial passo a passo para:
                {query}

                Inclua:
                - Objetivos de aprendizagem
                - Passos detalhados
                - Exemplos práticos
                """
            else:
                return f"""
                As a training specialist, create a step-by-step tutorial for:
                {query}

                Include:
                - Learning objectives
                - Detailed steps
                - Practical examples
                """

        else:  # knight
            if language == "pt":
                return f"Responda de forma clara e completa: {query}"
            else:
                return f"Answer clearly and completely: {query}"

    def _build_simple_prompt(self, query: str, agent: str, language: str) -> str:
        """Builds simple prompt for fast mode"""
        if language == "pt":
            prefix = {
                "bard": "Como analista, responda:",
                "wizard": "Como instrutor, explique:",
                "knight": "Responda:"
            }.get(agent, "Responda:")
        else:
            prefix = {
                "bard": "As an analyst, answer:",
                "wizard": "As an instructor, explain:",
                "knight": "Answer:"
            }.get(agent, "Answer:")

        return f"{prefix} {query}"

    def _generate_cache_key(self, query: str) -> str:
        """Generates cache key for query"""
        normalized = query.lower().strip()
        return f"multi_agent:{hashlib.md5(normalized.encode()).hexdigest()}"

    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Checks cache for result"""
        # Simple in-memory cache (can be replaced with Redis)
        return self._intent_cache.get(cache_key)

    def _save_to_cache(self, cache_key: str, result: Dict):
        """Saves result to cache"""
        # Simple in-memory cache with size limit
        if len(self._intent_cache) > 100:
            # Remove oldest entries
            self._intent_cache = dict(list(self._intent_cache.items())[-50:])

        self._intent_cache[cache_key] = result

    def _get_error_message(self, language: str) -> str:
        """Returns error message in appropriate language"""
        if language == "pt":
            return "Desculpe, ocorreu um erro ao processar sua solicitação."
        return "Sorry, an error occurred while processing your request."


# Global service instance
multi_agent_service = ConsolidatedMultiAgentService()