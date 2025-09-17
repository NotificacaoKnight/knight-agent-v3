"""
Hybrid Search Service combining PgVector and BM25
With FAISS fallback support
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.pgvector_service import PgVectorSearchService
from app.services.rag.bm25_service import BM25SearchService
from app.services.rag.faiss_service import FAISSSearchService
from app.core.config import settings

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Hybrid search service combining semantic and keyword search
    Uses pgvector as primary with FAISS fallback
    """

    def __init__(
        self,
        use_pgvector: bool = None,
        enable_fallback: bool = None,
        semantic_weight: float = None,
        keyword_weight: float = None
    ):
        """
        Initialize hybrid search service

        Args:
            use_pgvector: Whether to use pgvector (default from settings)
            enable_fallback: Whether to enable FAISS fallback
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
        """
        # Load configuration
        self.use_pgvector = use_pgvector if use_pgvector is not None else settings.USE_PGVECTOR
        self.enable_fallback = enable_fallback if enable_fallback is not None else settings.ENABLE_VECTOR_FALLBACK
        self.semantic_weight = semantic_weight if semantic_weight is not None else settings.SEMANTIC_WEIGHT
        self.keyword_weight = keyword_weight if keyword_weight is not None else settings.BM25_WEIGHT

        # Normalize weights
        total_weight = self.semantic_weight + self.keyword_weight
        if total_weight > 0:
            self.semantic_weight /= total_weight
            self.keyword_weight /= total_weight

        # Initialize services
        self.pgvector_service = None
        self.faiss_service = None
        self.bm25_service = BM25SearchService()

        # Initialize vector services based on configuration
        if self.use_pgvector:
            try:
                self.pgvector_service = PgVectorSearchService()
                logger.info("PgVector service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PgVector: {e}")
                if self.enable_fallback:
                    logger.info("Falling back to FAISS")
                    self._initialize_faiss()

        if not self.pgvector_service and self.enable_fallback:
            self._initialize_faiss()

    def _initialize_faiss(self):
        """Initialize FAISS as fallback"""
        try:
            self.faiss_service = FAISSSearchService()
            logger.info("FAISS service initialized as fallback")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS: {e}")

    async def search(
        self,
        query: str,
        k: int = 5,
        search_type: str = "hybrid",
        threshold: float = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search

        Args:
            query: Search query
            k: Number of results to return
            search_type: Type of search ("hybrid", "semantic", "keyword")
            threshold: Similarity/score threshold
            filter_conditions: Additional filters
            db: Database session

        Returns:
            List of search results
        """
        results = []

        try:
            if search_type in ["hybrid", "semantic"]:
                # Try semantic search
                semantic_results = await self._semantic_search(
                    query, k * 2, threshold, filter_conditions, db
                )
                results.extend(semantic_results)

            if search_type in ["hybrid", "keyword"]:
                # Try keyword search
                keyword_results = await self._keyword_search(
                    query, k * 2, threshold, filter_conditions, db
                )
                results.extend(keyword_results)

            # Combine and rank results
            if search_type == "hybrid":
                results = self._combine_results(
                    results,
                    self.semantic_weight,
                    self.keyword_weight
                )

            # Deduplicate and limit
            results = self._deduplicate_results(results)
            results = results[:k]

            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    async def _semantic_search(
        self,
        query: str,
        k: int,
        threshold: Optional[float],
        filter_conditions: Optional[Dict[str, Any]],
        db: Optional[AsyncSession]
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using vector service"""
        results = []

        # Try pgvector first
        if self.pgvector_service:
            try:
                results = await self.pgvector_service.search(
                    query, k, threshold, filter_conditions, db
                )
                # Add search type metadata
                for r in results:
                    r['search_type'] = 'pgvector'
                return results
            except Exception as e:
                logger.error(f"PgVector search failed: {e}")

        # Fallback to FAISS if enabled
        if self.faiss_service and self.enable_fallback:
            try:
                results = await self.faiss_service.search(
                    query, k, threshold, filter_conditions
                )
                # Add search type metadata
                for r in results:
                    r['search_type'] = 'faiss'
                return results
            except Exception as e:
                logger.error(f"FAISS search failed: {e}")

        return results

    async def _keyword_search(
        self,
        query: str,
        k: int,
        threshold: Optional[float],
        filter_conditions: Optional[Dict[str, Any]],
        db: Optional[AsyncSession]
    ) -> List[Dict[str, Any]]:
        """Perform keyword search using BM25"""
        try:
            filter_doc_ids = None
            if filter_conditions and 'document_ids' in filter_conditions:
                filter_doc_ids = filter_conditions['document_ids']

            results = await self.bm25_service.search(
                query, k, threshold, filter_doc_ids, db
            )

            # Add search type metadata
            for r in results:
                r['search_type'] = 'bm25'

            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def _combine_results(
        self,
        results: List[Dict[str, Any]],
        semantic_weight: float,
        keyword_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Combine and re-rank results from different search methods

        Args:
            results: List of all results
            semantic_weight: Weight for semantic results
            keyword_weight: Weight for keyword results

        Returns:
            Combined and ranked results
        """
        # Group results by chunk_id
        combined = {}

        for result in results:
            chunk_id = result.get('chunk_id')
            if not chunk_id:
                continue

            if chunk_id not in combined:
                combined[chunk_id] = {
                    **result,
                    'combined_score': 0,
                    'search_methods': []
                }

            # Add weighted score based on search type
            search_type = result.get('search_type')
            score = 0

            if search_type in ['pgvector', 'faiss']:
                # Semantic search - use similarity score
                score = result.get('similarity', 0) * semantic_weight
                combined[chunk_id]['semantic_score'] = result.get('similarity', 0)
            elif search_type == 'bm25':
                # Keyword search - normalize BM25 score
                bm25_score = result.get('score', 0)
                # Simple normalization (BM25 scores can vary widely)
                normalized_score = min(bm25_score / 10, 1.0)
                score = normalized_score * keyword_weight
                combined[chunk_id]['keyword_score'] = normalized_score

            combined[chunk_id]['combined_score'] += score
            combined[chunk_id]['search_methods'].append(search_type)

        # Sort by combined score
        ranked_results = sorted(
            combined.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )

        return ranked_results

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on chunk_id"""
        seen = set()
        deduplicated = []

        for result in results:
            chunk_id = result.get('chunk_id')
            if chunk_id and chunk_id not in seen:
                seen.add(chunk_id)
                deduplicated.append(result)

        return deduplicated

    async def build_indices(self, db: Optional[AsyncSession] = None):
        """Build or rebuild all search indices"""
        tasks = []

        # Build BM25 index
        logger.info("Building BM25 index...")
        await self.bm25_service.build_index(db)

        # Build vector indices if needed
        if self.pgvector_service:
            logger.info("Updating PgVector index...")
            await self.pgvector_service.update_index(db)

        if self.faiss_service:
            logger.info("Building FAISS index...")
            await self.faiss_service.build_index(db)

        logger.info("All indices built successfully")

    async def add_document(
        self,
        document_id: int,
        db: Optional[AsyncSession] = None
    ):
        """Add document to all indices"""
        # Add to vector store
        if self.pgvector_service:
            await self.pgvector_service.add_document_embeddings(document_id, db=db)
        elif self.faiss_service:
            await self.faiss_service.add_document_embeddings(document_id)

        # Update BM25 index
        await self.bm25_service.update_document(document_id, db)

    async def remove_document(
        self,
        document_id: int,
        db: Optional[AsyncSession] = None
    ):
        """Remove document from all indices"""
        # Remove from vector store
        if self.pgvector_service:
            await self.pgvector_service.remove_document_embeddings(document_id, db)
        elif self.faiss_service:
            await self.faiss_service.remove_document(document_id)

        # Update BM25 index
        await self.bm25_service.remove_document(document_id)

    async def get_stats(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Get statistics from all search services"""
        stats = {
            'hybrid_config': {
                'use_pgvector': self.use_pgvector,
                'enable_fallback': self.enable_fallback,
                'semantic_weight': self.semantic_weight,
                'keyword_weight': self.keyword_weight,
            }
        }

        # Get BM25 stats
        stats['bm25'] = await self.bm25_service.get_stats()

        # Get vector store stats
        if self.pgvector_service:
            stats['pgvector'] = await self.pgvector_service.get_stats(db)
        elif self.faiss_service:
            stats['faiss'] = await self.faiss_service.get_stats()

        return stats

    def clear_cache(self):
        """Clear all caches"""
        if self.pgvector_service:
            self.pgvector_service.clear_cache()
        if self.faiss_service:
            self.faiss_service.clear_cache()


# Synchronous version for Celery tasks
class HybridSearchServiceSync:
    """Synchronous version of hybrid search for Celery tasks"""

    def __init__(self):
        from app.services.rag.pgvector_service import PgVectorSearchServiceSync
        from app.services.rag.bm25_service import BM25SearchServiceSync

        self.pgvector_service = PgVectorSearchServiceSync()
        self.bm25_service = BM25SearchServiceSync()
        self.semantic_weight = settings.SEMANTIC_WEIGHT
        self.keyword_weight = settings.BM25_WEIGHT

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Synchronous hybrid search"""
        results = []

        # Semantic search
        # Note: Would need to implement sync pgvector search
        # For now, skip semantic in sync version

        # Keyword search
        keyword_results = self.bm25_service.search(query, k * 2)
        results.extend(keyword_results)

        return results[:k]


# Global singleton instance
_hybrid_search_service_instance: Optional[HybridSearchService] = None


def get_hybrid_search_service() -> HybridSearchService:
    """
    Get singleton instance of HybridSearchService
    This ensures the service is initialized only once across the entire application
    """
    global _hybrid_search_service_instance

    if _hybrid_search_service_instance is None:
        logger.info("🔍 Initializing global HybridSearchService singleton")
        _hybrid_search_service_instance = HybridSearchService()

    return _hybrid_search_service_instance