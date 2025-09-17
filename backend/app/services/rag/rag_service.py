"""
Main RAG Service for FastAPI
Integrates search, LLM generation, and response formatting
"""
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

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

        try:
            # Step 1: Search for relevant chunks
            search_results = await self.search(
                query=query,
                k=context_size,
                search_type="hybrid",
                filter_document_ids=filter_document_ids,
                db=db
            )

            if not search_results['success'] or not search_results['results']:
                return {
                    'success': False,
                    'query': query,
                    'answer': self._get_no_results_message(language),
                    'sources': [],
                    'error': 'No relevant context found',
                    'response_time_ms': int((time.time() - start_time) * 1000)
                }

            # Step 2: Build context from search results
            context = self._build_context(search_results['results'], language)

            # Step 3: Create prompt
            prompt = self._create_prompt(query, language)

            # Step 4: Generate answer with LLM
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
                # Use fallback chain
                answer, provider_used = await self.llm_manager.generate_with_fallback(
                    prompt=prompt,
                    context=context,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            # Step 5: Format response
            response = {
                'success': True,
                'query': query,
                'answer': answer,
                'llm_provider': str(provider_used),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

            if include_sources:
                response['sources'] = search_results['results'][:3]  # Top 3 sources

            return response

        except Exception as e:
            logger.error(f"RAG generation error: {e}")
            return {
                'success': False,
                'query': query,
                'answer': self._get_error_message(language),
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }

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

    def _get_no_results_message(self, language: str) -> str:
        """Get no results message"""
        if language == "pt":
            return "Desculpe, não encontrei informações relevantes para responder sua pergunta."
        return "Sorry, I couldn't find relevant information to answer your question."

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