"""
RAG API endpoints for FastAPI
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_optional_current_user, get_current_user
from app.models.user import User
from app.schemas.rag import (
    SearchQuery,
    SearchResponse,
    RAGQuery,
    RAGResponse,
    AgenticRAGQuery,
    AgenticRAGResponse,
    VectorStatsResponse,
    LLMProvidersResponse,
    LLMProviderInfo,
    TestLLMQuery,
    TestLLMResponse,
    ChunkResult
)
from app.services.rag.rag_service import rag_service
from app.services.rag.llm_providers import ProviderType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["RAG"])


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    query: SearchQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Search documents using hybrid search (semantic + keyword)

    - **query**: Search query text
    - **k**: Number of results to return (1-20)
    - **search_type**: Type of search (hybrid, semantic, keyword)
    - **threshold**: Similarity threshold (0.0-1.0)
    - **filter_document_ids**: Optional list of document IDs to filter
    """
    try:
        # Log search request
        logger.info(f"Search request: query='{query.query}', k={query.k}, type={query.search_type}")

        # Check if we should use agentic RAG (future implementation)
        if query.use_agentic:
            # TODO: Implement agentic RAG with LangGraph
            logger.warning("Agentic RAG not yet implemented, falling back to standard search")

        # Perform search
        result = await rag_service.search(
            query=query.query,
            k=query.k,
            search_type=query.search_type,
            threshold=query.threshold,
            filter_document_ids=query.filter_document_ids,
            db=db
        )

        # Convert to response model
        chunks = []
        for r in result.get('results', []):
            chunk = ChunkResult(
                chunk_id=r['chunk_id'],
                document_id=r['document_id'],
                document_title=r.get('document_title'),
                content=r['content'],
                chunk_index=r['chunk_index'],
                similarity=r.get('similarity'),
                score=r.get('score'),
                page_number=r.get('page_number'),
                section_title=r.get('section_title'),
                highlights=r.get('highlights')
            )
            chunks.append(chunk)

        return SearchResponse(
            success=result['success'],
            query=result['query'],
            results=chunks,
            total_results=result['total_results'],
            search_type=result['search_type'],
            search_time_ms=result['search_time_ms'],
            metadata=result.get('metadata')
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=RAGResponse)
async def generate_answer(
    query: RAGQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Generate answer using RAG (Retrieval-Augmented Generation)

    - **query**: User question
    - **context_size**: Number of context chunks to use
    - **max_tokens**: Maximum tokens in response
    - **temperature**: Generation temperature (0.0-1.0)
    - **include_sources**: Include source references
    - **language**: Response language (pt, en)
    - **llm_provider**: Specific LLM provider to use
    """
    try:
        logger.info(f"Generate request: query='{query.query}', context_size={query.context_size}")

        # Check if we should use agentic RAG
        if query.use_agentic:
            # TODO: Implement agentic RAG with LangGraph
            logger.warning("Agentic RAG not yet implemented, falling back to standard generation")

        # Generate answer
        result = await rag_service.generate_answer(
            query=query.query,
            context_size=query.context_size,
            max_tokens=query.max_tokens,
            temperature=query.temperature,
            include_sources=query.include_sources,
            language=query.language,
            llm_provider=query.llm_provider,
            db=db
        )

        # Convert sources to ChunkResult if included
        sources = None
        if result.get('sources'):
            sources = []
            for s in result['sources']:
                source = ChunkResult(
                    chunk_id=s['chunk_id'],
                    document_id=s['document_id'],
                    document_title=s.get('document_title'),
                    content=s['content'],
                    chunk_index=s['chunk_index'],
                    similarity=s.get('similarity'),
                    score=s.get('score'),
                    page_number=s.get('page_number'),
                    section_title=s.get('section_title')
                )
                sources.append(source)

        return RAGResponse(
            success=result['success'],
            query=result['query'],
            answer=result['answer'],
            sources=sources,
            llm_provider=result.get('llm_provider', 'unknown'),
            response_time_ms=result['response_time_ms'],
            tokens_used=result.get('tokens_used'),
            metadata=result.get('metadata')
        )

    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agentic", response_model=AgenticRAGResponse)
async def agentic_generate(
    query: AgenticRAGQuery,
    db: AsyncSession = Depends(get_async_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Generate answer using Agentic RAG with LangGraph

    Advanced RAG with multi-step reasoning, search refinement, and quality evaluation
    """
    try:
        logger.info(f"Agentic RAG request: query='{query.query}'")

        # Import agentic service
        from app.services.rag.agentic_rag_service import agentic_rag_service

        # Execute agentic RAG
        result = await agentic_rag_service.search(
            query=query.query,
            k=query.max_documents,
            language="pt",
            chat_history=[]
        )

        # Convert sources to ChunkResult
        sources = []
        for s in result.get('sources', []):
            source = ChunkResult(
                chunk_id=s.get('chunk_id', 0),
                document_id=s.get('document_id', 0),
                document_title=s.get('document_title'),
                content=s.get('content', ''),
                chunk_index=s.get('chunk_index', 0),
                similarity=s.get('similarity'),
                score=s.get('score')
            )
            sources.append(source)

        # Import multi-agent service for advanced features
        if query.enable_multi_agent:
            from app.services.rag.multi_agent_service import multi_agent_service

            multi_result = await multi_agent_service.process_query(
                query=query.query,
                force_mode="complete" if query.agent_type else None,
                user_language="pt"
            )

            agent_used = multi_result.get("agent", query.agent_type)
            reasoning_steps = multi_result.get("execution_path", [])
        else:
            agent_used = query.agent_type
            reasoning_steps = []

        return AgenticRAGResponse(
            success=result['success'],
            query=result['query'],
            answer=result['answer'],
            sources=sources,
            search_refinements=result.get('search_refinements', 0),
            quality_score=result.get('quality_score', 0.0),
            agent_used=agent_used,
            useful_links=[],  # TODO: Add knowledge resources
            downloadable_documents=[],  # TODO: Add knowledge resources
            reasoning_steps=reasoning_steps,
            llm_provider=result.get('llm_provider', 'unknown'),
            response_time_ms=result['response_time_ms'],
            metadata=result.get('metadata', {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agentic RAG error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=VectorStatsResponse)
async def get_vector_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get vector store statistics

    Returns information about documents, chunks, and embeddings
    """
    try:
        stats = await rag_service.get_stats(db)

        search_stats = stats.get('search', {})

        return VectorStatsResponse(
            total_documents=search_stats.get('total_documents', 0),
            total_chunks=search_stats.get('total_chunks', 0),
            chunks_with_embeddings=search_stats.get('chunks_with_embeddings', 0),
            embedding_coverage=search_stats.get('embedding_coverage', 0.0),
            service_type=search_stats.get('service_type', 'unknown'),
            embedding_model=search_stats.get('embedding_model', 'unknown'),
            embedding_dimension=search_stats.get('embedding_dimension', 0),
            index_status=search_stats.get('index_status')
        )

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=LLMProvidersResponse)
async def get_llm_providers(
    current_user: User = Depends(get_current_user)
):
    """
    Get available LLM providers

    Returns list of configured LLM providers and their status
    """
    try:
        providers = rag_service.llm_manager.get_available_providers()

        provider_infos = []
        for p in providers:
            info = LLMProviderInfo(
                type=str(p['type']),
                available=p['available'],
                info=p.get('info'),
                error=p.get('error')
            )
            provider_infos.append(info)

        # Get fallback order
        fallback_order = [str(p) for p in rag_service.llm_manager.fallback_order]

        # Get current provider from settings
        from app.core.config import settings
        current = settings.LLM_PROVIDER or "deepseek"

        return LLMProvidersResponse(
            providers=provider_infos,
            current_provider=current,
            fallback_order=fallback_order
        )

    except Exception as e:
        logger.error(f"Providers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-llm", response_model=TestLLMResponse)
async def test_llm_provider(
    query: TestLLMQuery,
    current_user: User = Depends(get_current_user)
):
    """
    Test LLM provider

    Send a test prompt to a specific LLM provider
    """
    try:
        result = await rag_service.test_llm(
            prompt=query.prompt,
            provider=query.provider,
            max_tokens=query.max_tokens,
            temperature=query.temperature
        )

        return TestLLMResponse(
            success=result['success'],
            provider=result['provider'],
            response=result.get('response'),
            error=result.get('error'),
            response_time_ms=result['response_time_ms']
        )

    except Exception as e:
        logger.error(f"Test LLM error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build-indices")
async def build_search_indices(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Build or rebuild search indices

    Recreates BM25 index and optimizes vector indices
    """
    try:
        await rag_service.build_indices(db)

        return {
            "success": True,
            "message": "Search indices rebuilt successfully"
        }

    except Exception as e:
        logger.error(f"Build indices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def rag_health_check():
    """
    RAG system health check

    Verifies all RAG components are operational
    """
    try:
        # Check search service
        search_healthy = True
        try:
            test_result = await rag_service.search("test", k=1)
            search_healthy = test_result.get('success', False)
        except:
            search_healthy = False

        # Check LLM providers
        providers_healthy = True
        try:
            providers = rag_service.llm_manager.get_available_providers()
            providers_healthy = any(p['available'] for p in providers)
        except:
            providers_healthy = False

        overall_healthy = search_healthy and providers_healthy

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "components": {
                "search": "healthy" if search_healthy else "unhealthy",
                "llm_providers": "healthy" if providers_healthy else "unhealthy"
            }
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }