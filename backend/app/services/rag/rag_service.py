"""
Main RAG Service for FastAPI
Integrates search, LLM generation, and response formatting
Unified service with fast/deep/auto modes
"""
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Literal
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.hybrid_search_service import get_hybrid_search_service
from app.services.rag.llm_providers import llm_manager, ProviderType
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    Main RAG service for question answering
    Combines search and generation
    """

    def __init__(self):
        self.search_service = get_hybrid_search_service()
        self.llm_manager = llm_manager

    async def search(
        self,
        query: str,
        k: int = 5,
        search_type: str = "hybrid",
        threshold: Optional[float] = None,
        filter_document_ids: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Perform search only

        Args:
            query: Search query
            k: Number of results
            search_type: Type of search
            threshold: Similarity threshold
            filter_document_ids: Document filter
            db: Database session

        Returns:
            Search results
        """
        start_time = time.time()

        try:
            # Build filter conditions
            filter_conditions = {}
            if filter_document_ids:
                filter_conditions['document_ids'] = filter_document_ids

            # Perform search
            results = await self.search_service.search(
                query=query,
                k=k,
                search_type=search_type,
                threshold=threshold,
                filter_conditions=filter_conditions,
                db=db
            )

            search_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': True,
                'query': query,
                'results': results,
                'total_results': len(results),
                'search_type': search_type,
                'search_time_ms': search_time_ms
            }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'success': False,
                'query': query,
                'results': [],
                'total_results': 0,
                'error': str(e),
                'search_time_ms': int((time.time() - start_time) * 1000)
            }

    async def generate_answer(
        self,
        query: str,
        mode: Literal["fast", "deep", "auto"] = "auto",
        context_size: int = 5,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        include_sources: bool = True,
        language: str = "pt",
        llm_provider: Optional[str] = None,
        filter_document_ids: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Generate answer using RAG

        Args:
            query: User question
            mode: Response mode (fast/deep/auto)
            context_size: Number of context chunks
            max_tokens: Maximum tokens in response
            temperature: Generation temperature
            include_sources: Include source references
            language: Response language
            llm_provider: Specific LLM provider
            filter_document_ids: Document filter
            db: Database session

        Returns:
            Generated answer with sources
        """
        start_time = time.time()

        # Auto-detect complexity if mode is auto
        if mode == "auto":
            mode = self._detect_complexity(query)
            logger.info(f"Auto-detected mode: {mode} for query: {query}")

        # Route to appropriate pipeline
        if mode == "fast":
            return await self._fast_pipeline(
                query=query,
                context_size=context_size,
                max_tokens=max_tokens,
                temperature=temperature,
                include_sources=include_sources,
                language=language,
                llm_provider=llm_provider,
                filter_document_ids=filter_document_ids,
                db=db,
                start_time=start_time
            )
        else:  # deep mode
            return await self._deep_pipeline(
                query=query,
                context_size=context_size,
                max_tokens=max_tokens,
                temperature=temperature,
                include_sources=include_sources,
                language=language,
                llm_provider=llm_provider,
                filter_document_ids=filter_document_ids,
                db=db,
                start_time=start_time
            )

    def _detect_complexity(self, query: str) -> str:
        """Detect if query needs deep analysis"""
        # Complex keywords that indicate need for deep analysis
        complex_keywords = [
            "como", "por que", "porque", "explique", "detalhe", "detalhes",
            "processo", "procedimento", "cálculo", "calcular", "passos",
            "compare", "analise", "quando devo", "o que fazer",
            "passo a passo", "tutorial", "configurar", "implementar"
        ]

        # Simple keywords that indicate fast response is enough
        simple_keywords = [
            "qual", "onde", "quem", "quando", "horário", "telefone",
            "email", "endereço", "nome", "data", "número", "código"
        ]

        query_lower = query.lower()

        # Check for simple queries first
        if any(kw in query_lower for kw in simple_keywords) and len(query) < 50:
            return "fast"

        # Check for complex queries
        if len(query) > 100 or any(kw in query_lower for kw in complex_keywords):
            return "deep"

        # Default to fast for short queries
        return "fast" if len(query) < 30 else "deep"

    async def _fast_pipeline(
        self,
        query: str,
        context_size: int,
        max_tokens: int,
        temperature: float,
        include_sources: bool,
        language: str,
        llm_provider: Optional[str],
        filter_document_ids: Optional[List[int]],
        db: Optional[AsyncSession],
        start_time: float
    ) -> Dict[str, Any]:
        """Fast pipeline - simple search and generation"""
        try:
            # Search for relevant chunks
            search_results = await self.search(
                query=query,
                k=context_size,
                search_type="hybrid",
                filter_document_ids=filter_document_ids,
                db=db
            )

            # Build context (empty if no results)
            context = ""
            if search_results['success'] and search_results['results']:
                context = self._build_context(search_results['results'], language)

            # Always try to generate response, even without context
            prompt = self._create_prompt(query, language)

            # Generate answer with LLM
            if llm_provider:
                provider = self.llm_manager.get_provider(ProviderType(llm_provider))
                answer = await provider.generate_with_context(
                    prompt=prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                provider_used = llm_provider
            else:
                answer, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            # Format response
            response = {
                'success': True,
                'query': query,
                'answer': answer,
                'mode': 'fast',
                'llm_provider': str(provider_used),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

            if include_sources and search_results.get('results'):
                response['sources'] = search_results['results'][:3]

            return response

        except Exception as e:
            logger.error(f"Fast pipeline error: {e}")
            return {
                'success': False,
                'query': query,
                'answer': self._get_error_message(language),
                'mode': 'fast',
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

    async def _deep_pipeline(
        self,
        query: str,
        context_size: int,
        max_tokens: int,
        temperature: float,
        include_sources: bool,
        language: str,
        llm_provider: Optional[str],
        filter_document_ids: Optional[List[int]],
        db: Optional[AsyncSession],
        start_time: float
    ) -> Dict[str, Any]:
        """Deep pipeline - multi-step reasoning with refinement"""
        try:
            max_attempts = 3
            best_results = []
            search_attempts = 0
            refined_queries = [query]

            # Multiple search attempts with query refinement
            for attempt in range(max_attempts):
                search_query = refined_queries[-1]

                # Search with current query
                search_results = await self.search(
                    query=search_query,
                    k=context_size * 2,  # Get more results for better selection
                    search_type="hybrid",
                    filter_document_ids=filter_document_ids,
                    db=db
                )

                search_attempts += 1

                # Evaluate search quality
                if search_results['success'] and search_results['results']:
                    # Calculate average score
                    avg_score = sum(r.get('score', 0) for r in search_results['results']) / len(search_results['results'])

                    # If good results, use them
                    if avg_score > 0.6 or len(search_results['results']) >= 3:
                        best_results = search_results['results']
                        break

                    # Keep best results so far
                    if len(search_results['results']) > len(best_results):
                        best_results = search_results['results']

                # Try to refine query for next attempt
                if attempt < max_attempts - 1:
                    refined_query = await self._refine_query(query, search_query, language)
                    if refined_query and refined_query != search_query:
                        refined_queries.append(refined_query)
                    else:
                        break  # Can't refine further

            # Build context from best results
            context = ""
            if best_results:
                # Select most relevant chunks
                selected_chunks = self._select_best_chunks(best_results, context_size)
                context = self._build_context(selected_chunks, language)

            # Generate response with enriched prompt for deep mode
            prompt = self._create_deep_prompt(query, language)

            # Generate answer
            if llm_provider:
                provider = self.llm_manager.get_provider(ProviderType(llm_provider))
                answer = await provider.generate_with_context(
                    prompt=prompt,
                    context=context,
                    max_tokens=max_tokens * 2,  # Allow longer responses in deep mode
                    temperature=temperature
                )
                provider_used = llm_provider
            else:
                answer, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=prompt,
                    context=context,
                    max_tokens=max_tokens * 2,
                    temperature=temperature
                )

            # Format response
            response = {
                'success': True,
                'query': query,
                'answer': answer,
                'mode': 'deep',
                'search_attempts': search_attempts,
                'refined_queries': refined_queries if len(refined_queries) > 1 else None,
                'llm_provider': str(provider_used),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

            if include_sources and best_results:
                response['sources'] = best_results[:5]  # More sources in deep mode

            return response

        except Exception as e:
            logger.error(f"Deep pipeline error: {e}")
            # Fallback to fast pipeline on error
            return await self._fast_pipeline(
                query=query,
                context_size=context_size,
                max_tokens=max_tokens,
                temperature=temperature,
                include_sources=include_sources,
                language=language,
                llm_provider=llm_provider,
                filter_document_ids=filter_document_ids,
                db=db,
                start_time=start_time
            )

    async def _refine_query(self, original_query: str, current_query: str, language: str) -> Optional[str]:
        """Use LLM to refine search query"""
        try:
            if language == "pt":
                refinement_prompt = f"""
                A busca por '{current_query}' retornou poucos resultados relevantes.
                Query original: '{original_query}'

                Sugira uma query de busca refinada que possa encontrar melhores resultados.
                Considere sinônimos, termos relacionados ou reformulações.

                Query refinada:"""
            else:
                refinement_prompt = f"""
                The search for '{current_query}' returned few relevant results.
                Original query: '{original_query}'

                Suggest a refined search query that might find better results.
                Consider synonyms, related terms, or reformulations.

                Refined query:"""

            refined, _ = await self.llm_manager.generate_with_fallback(
                prompt=refinement_prompt,
                max_tokens=100,
                temperature=0.3
            )

            return refined.strip() if refined else None

        except Exception as e:
            logger.error(f"Query refinement error: {e}")
            return None

    def _select_best_chunks(self, chunks: List[Dict[str, Any]], max_chunks: int) -> List[Dict[str, Any]]:
        """Select best chunks based on score and diversity"""
        # Sort by score
        sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)

        # Select top chunks ensuring document diversity
        selected = []
        seen_docs = set()

        for chunk in sorted_chunks:
            if len(selected) >= max_chunks:
                break

            doc_id = chunk.get('document_id')
            # Add chunk if from new document or high score
            if doc_id not in seen_docs or chunk.get('score', 0) > 0.8:
                selected.append(chunk)
                seen_docs.add(doc_id)

        return selected

    def _create_deep_prompt(self, query: str, language: str) -> str:
        """Create enriched prompt for deep mode"""
        if language == "pt":
            return f"""
            Analise cuidadosamente o contexto fornecido e responda à pergunta de forma completa e detalhada.
            Se o contexto não contiver informações suficientes, use seu conhecimento para complementar a resposta de forma útil.
            Seja específico e forneça exemplos quando apropriado.

            Pergunta: {query}

            Responda em português brasileiro de forma clara e estruturada.
            """
        else:
            return f"""
            Carefully analyze the provided context and answer the question completely and in detail.
            If the context doesn't contain enough information, use your knowledge to complement the answer helpfully.
            Be specific and provide examples when appropriate.

            Question: {query}

            Answer in English clearly and with structure.
            """

    def _build_context(self, chunks: List[Dict[str, Any]], language: str) -> str:
        """Build context from search results"""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            # Add source reference
            doc_title = chunk.get('document_title', f"Document {chunk.get('document_id')}")
            page = chunk.get('page_number')

            if page:
                source_ref = f"[{i}. {doc_title} - Página {page}]"
            else:
                source_ref = f"[{i}. {doc_title}]"

            context_parts.append(f"{source_ref}\n{chunk['content']}\n")

        return "\n".join(context_parts)

    def _create_prompt(self, query: str, language: str) -> str:
        """Create prompt for LLM"""
        if language == "pt":
            return f"""
Com base no contexto fornecido, responda à seguinte pergunta de forma clara e precisa.
Se a resposta não estiver no contexto, diga que não há informações suficientes.

Pergunta: {query}

Responda em português brasileiro.
"""
        else:
            return f"""
Based on the provided context, answer the following question clearly and precisely.
If the answer is not in the context, say there is not enough information.

Question: {query}

Answer in English.
"""


    def _get_error_message(self, language: str) -> str:
        """Get error message"""
        if language == "pt":
            return "Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente novamente."
        return "Sorry, an error occurred while processing your question. Please try again."

    async def get_stats(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Get RAG system statistics"""
        stats = {
            'search': await self.search_service.get_stats(db),
            'llm_providers': self.llm_manager.get_available_providers()
        }
        return stats

    async def build_indices(self, db: Optional[AsyncSession] = None):
        """Build or rebuild search indices"""
        await self.search_service.build_indices(db)

    async def test_llm(
        self,
        prompt: str,
        provider: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Test LLM provider"""
        start_time = time.time()

        try:
            if provider:
                llm_provider = self.llm_manager.get_provider(ProviderType(provider))
                response = await llm_provider.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                provider_used = provider
            else:
                response, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            return {
                'success': True,
                'provider': str(provider_used),
                'response': response,
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            return {
                'success': False,
                'provider': provider or 'unknown',
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }


# Global RAG service instance
rag_service = RAGService()