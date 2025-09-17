"""
Agentic RAG Service using LangGraph
Implements agentic patterns with dynamic decision-making, self-reflection and multi-step reasoning
"""
import time
import logging
from typing import Dict, List, Any, Optional, TypedDict, Literal
from datetime import datetime

try:
    from langgraph.graph import StateGraph, START, END
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None
    BaseMessage = None
    HumanMessage = None
    AIMessage = None

from app.services.rag.hybrid_search_service import get_hybrid_search_service
from app.services.rag.llm_providers import llm_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgenticRAGState(TypedDict):
    """Shared state between graph nodes"""
    # Input/Output
    query: str
    messages: List[BaseMessage] if HAS_LANGGRAPH else List[Dict]
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

    # Knowledge resources
    useful_links: List[Dict[str, Any]]
    downloadable_documents: List[Dict[str, Any]]

    # Quality control
    response_quality: float
    needs_refinement: bool

    # Chat context and language
    chat_history: List[Dict[str, Any]]
    user_language: str

    # Metadata
    search_duration_ms: int
    total_duration_ms: int
    provider_used: str
    next_action: Literal["search", "refine_query", "generate", "validate", "end"]


class AgenticRAGService:
    """Agentic RAG Service using LangGraph"""

    def __init__(self):
        self.search_service = get_hybrid_search_service()
        self.llm_manager = llm_manager

        # Configuration
        self.max_search_attempts = settings.AGENTIC_MAX_SEARCH_ATTEMPTS if hasattr(settings, 'AGENTIC_MAX_SEARCH_ATTEMPTS') else 3
        self.quality_threshold = settings.AGENTIC_QUALITY_THRESHOLD if hasattr(settings, 'AGENTIC_QUALITY_THRESHOLD') else 0.6
        self.max_context_length = settings.AGENTIC_MAX_CONTEXT_LENGTH if hasattr(settings, 'AGENTIC_MAX_CONTEXT_LENGTH') else 8000

        # Create graph if LangGraph is available
        self.graph = self._create_graph() if HAS_LANGGRAPH else None

    def _create_graph(self) -> StateGraph:
        """Creates the simplified LangGraph state graph"""
        if not HAS_LANGGRAPH:
            return None

        workflow = StateGraph(AgenticRAGState)

        # Essential nodes only
        workflow.add_node("searcher", self._search_node)
        workflow.add_node("quality_checker", self._quality_check_node)
        workflow.add_node("query_refiner", self._query_refinement_node)
        workflow.add_node("generator", self._generation_node)

        # Simplified flow
        workflow.add_edge(START, "searcher")
        workflow.add_edge("searcher", "quality_checker")

        # Simplified conditional routing
        workflow.add_conditional_edges(
            "quality_checker",
            self._quality_router,
            {
                "refine": "query_refiner",
                "generate": "generator",
                "end": END
            }
        )

        workflow.add_edge("query_refiner", "searcher")
        workflow.add_edge("generator", END)

        return workflow.compile()

    async def _search_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Search execution node"""
        start_time = time.time()

        try:
            # Perform hybrid search
            results = await self.search_service.search(
                query=state["query"],
                k=10,
                search_type="hybrid"
            )

            state["search_results"] = results
            state["search_attempts"] = state.get("search_attempts", 0) + 1

            # Calculate quality score
            if results:
                avg_score = sum(r.get("score", 0) for r in results) / len(results)
                state["search_quality_score"] = avg_score
            else:
                state["search_quality_score"] = 0.0

            # Extract documents
            state["retrieved_documents"] = [
                r.get("content", "") for r in results
            ]

        except Exception as e:
            logger.error(f"Search node error: {e}")
            state["search_results"] = []
            state["search_quality_score"] = 0.0
            state["retrieved_documents"] = []

        state["search_duration_ms"] = int((time.time() - start_time) * 1000)
        return state

    async def _quality_check_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Quality evaluation node"""
        score = state.get("search_quality_score", 0)
        attempts = state.get("search_attempts", 0)

        if score < self.quality_threshold and attempts < self.max_search_attempts:
            state["needs_refinement"] = True
            state["next_action"] = "refine"
        elif state.get("retrieved_documents"):
            state["needs_refinement"] = False
            state["next_action"] = "generate"
        else:
            state["next_action"] = "end"

        return state

    def _quality_router(self, state: AgenticRAGState) -> str:
        """Routes based on quality check results"""
        return state.get("next_action", "end")

    async def _query_refinement_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Query refinement node using LLM"""
        try:
            # Use LLM to refine query
            prompt = f"""
            The search for '{state["query"]}' returned poor results.
            Please suggest a refined query that might return better results.
            Consider synonyms, related terms, or more specific phrasing.

            Refined query:
            """

            refined_query, provider = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                max_tokens=100,
                temperature=0.3
            )

            if refined_query:
                state["query"] = refined_query.strip()

        except Exception as e:
            logger.error(f"Query refinement error: {e}")

        return state

    async def _generation_node(self, state: AgenticRAGState) -> AgenticRAGState:
        """Response generation node"""
        start_time = time.time()

        try:
            # Build context
            context = "\n\n".join(state.get("retrieved_documents", []))[:self.max_context_length]

            # Determine language
            language = state.get("user_language", "pt")

            # Create prompt
            if language == "pt":
                prompt = f"""
                Com base no contexto fornecido, responda à pergunta de forma clara e precisa.

                Pergunta: {state["query"]}

                Responda em português brasileiro.
                """
            else:
                prompt = f"""
                Based on the provided context, answer the question clearly and precisely.

                Question: {state["query"]}

                Answer in English.
                """

            # Generate response
            response, provider = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                context=context,
                max_tokens=1000,
                temperature=0.7
            )

            state["final_response"] = response
            state["provider_used"] = str(provider)

        except Exception as e:
            logger.error(f"Generation node error: {e}")
            state["final_response"] = self._get_error_message(language)
            state["provider_used"] = "error"

        total_time = int((time.time() - start_time) * 1000)
        state["total_duration_ms"] = state.get("search_duration_ms", 0) + total_time

        return state

    def _get_error_message(self, language: str) -> str:
        """Get error message in the appropriate language"""
        if language == "pt":
            return "Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente."
        return "Sorry, an error occurred while processing your question. Please try again."

    async def search(
        self,
        query: str,
        k: int = 5,
        language: str = "pt",
        chat_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute agentic RAG search

        Args:
            query: Search query
            k: Number of results
            language: Response language
            chat_history: Optional chat history

        Returns:
            Dict with response and metadata
        """
        start_time = time.time()

        # Check if LangGraph is available
        if not HAS_LANGGRAPH or not self.graph:
            # Fallback to simple hybrid search
            return await self._simple_rag(query, k, language)

        try:
            # Initialize state
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
                useful_links=[],
                downloadable_documents=[],
                response_quality=0.0,
                needs_refinement=False,
                chat_history=chat_history or [],
                user_language=language,
                search_duration_ms=0,
                total_duration_ms=0,
                provider_used="",
                next_action="search"
            )

            # Execute graph
            result = await self.graph.ainvoke(initial_state)

            # Format response
            return {
                "success": True,
                "query": query,
                "answer": result.get("final_response", ""),
                "sources": result.get("search_results", [])[:k],
                "search_refinements": result.get("search_attempts", 1) - 1,
                "quality_score": result.get("search_quality_score", 0),
                "llm_provider": result.get("provider_used", "unknown"),
                "response_time_ms": int((time.time() - start_time) * 1000),
                "metadata": {
                    "agentic": True,
                    "search_duration_ms": result.get("search_duration_ms", 0),
                    "total_duration_ms": result.get("total_duration_ms", 0)
                }
            }

        except Exception as e:
            logger.error(f"Agentic RAG error: {e}")
            # Fallback to simple RAG
            return await self._simple_rag(query, k, language)

    async def _simple_rag(self, query: str, k: int, language: str) -> Dict[str, Any]:
        """Simple RAG fallback without LangGraph"""
        start_time = time.time()

        try:
            # Perform search
            search_results = await self.search_service.search(
                query=query,
                k=k,
                search_type="hybrid"
            )

            if not search_results:
                return {
                    "success": False,
                    "query": query,
                    "answer": self._get_no_results_message(language),
                    "sources": [],
                    "response_time_ms": int((time.time() - start_time) * 1000)
                }

            # Build context
            context = "\n\n".join([r.get("content", "") for r in search_results])[:self.max_context_length]

            # Create prompt
            if language == "pt":
                prompt = f"Com base no contexto, responda: {query}"
            else:
                prompt = f"Based on the context, answer: {query}"

            # Generate response
            response, provider = await self.llm_manager.generate_with_fallback(
                prompt=prompt,
                context=context,
                max_tokens=1000,
                temperature=0.7
            )

            return {
                "success": True,
                "query": query,
                "answer": response,
                "sources": search_results[:k],
                "llm_provider": str(provider),
                "response_time_ms": int((time.time() - start_time) * 1000),
                "metadata": {
                    "agentic": False,
                    "fallback": True
                }
            }

        except Exception as e:
            logger.error(f"Simple RAG error: {e}")
            return {
                "success": False,
                "query": query,
                "answer": self._get_error_message(language),
                "error": str(e),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }

    def _get_no_results_message(self, language: str) -> str:
        """Get no results message"""
        if language == "pt":
            return "Desculpe, não encontrei informações relevantes para responder sua pergunta."
        return "Sorry, I couldn't find relevant information to answer your question."


# Sync version for Celery compatibility
class AgenticRAGServiceSync:
    """Synchronous version of AgenticRAGService for Celery tasks"""

    def __init__(self):
        from app.services.rag.hybrid_search_service import HybridSearchServiceSync
        self.search_service = HybridSearchServiceSync()
        self.llm_manager = llm_manager
        self.max_search_attempts = 3
        self.quality_threshold = 0.6
        self.max_context_length = 8000

    def search(self, query: str, k: int = 5, language: str = "pt", **kwargs) -> Dict[str, Any]:
        """Synchronous search for Celery tasks"""
        import asyncio

        # Create new event loop for sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Create async service and run
            async_service = AgenticRAGService()
            result = loop.run_until_complete(
                async_service.search(query, k, language, **kwargs)
            )
            return result
        finally:
            loop.close()


# Global service instance
agentic_rag_service = AgenticRAGService()