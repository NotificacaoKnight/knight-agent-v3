"""
PgVector Search Service for FastAPI
Production-ready implementation with concurrent access support
"""
import numpy as np
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
# Session import removed - using only AsyncSession for FastAPI compatibility

# Try to import pgvector, but make it optional
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None

from app.core.database import get_async_db
from app.models import Document, DocumentChunk
from app.core.config import settings

# Try to import EmbeddingService, but make it optional
try:
    from app.services.embedding_service import get_embedding_service
    HAS_EMBEDDING_SERVICE = True
except ImportError:
    HAS_EMBEDDING_SERVICE = False
    get_embedding_service = None

logger = logging.getLogger(__name__)


class PgVectorIndexManager:
    """Manages pgvector indexes for optimal performance"""

    @staticmethod
    async def create_optimal_index(
        db: AsyncSession,
        table_name: str = 'document_chunks',
        field_name: str = 'embedding'
    ):
        """Create optimal index based on data size"""
        try:
            # Check current row count
            result = await db.execute(
                text(f"SELECT COUNT(*) FROM {table_name} WHERE {field_name} IS NOT NULL")
            )
            row_count = result.scalar()

            logger.info(f"Creating index for {row_count} vectors")

            if row_count < 100000:
                # For smaller datasets: HNSW with cosine distance
                index_sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {field_name}_hnsw_cosine_idx
                ON {table_name}
                USING hnsw ({field_name} vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
                """
                logger.info("Creating HNSW index for optimal performance")
            else:
                # For larger datasets: IVFFlat with more lists
                lists = max(row_count // 1000, 100)  # rows/1000, minimum 100
                index_sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {field_name}_ivfflat_cosine_idx
                ON {table_name}
                USING ivfflat ({field_name} vector_cosine_ops)
                WITH (lists = {lists});
                """
                logger.info(f"Creating IVFFlat index with {lists} lists")

            await db.execute(text(index_sql))
            await db.commit()
            logger.info("Index created successfully")

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    @staticmethod
    async def optimize_query_parameters(db: AsyncSession):
        """Set optimal query parameters for similarity search"""
        try:
            # For HNSW indexes
            await db.execute(text("SET hnsw.ef_search = 64"))  # Higher for better recall

            # For IVFFlat indexes
            await db.execute(text("SET ivfflat.probes = 10"))  # sqrt(lists) approximately

            logger.debug("Query parameters optimized")
        except Exception as e:
            logger.warning(f"Could not optimize query parameters: {e}")


class PgVectorSearchService:
    """Production-ready pgvector search service with concurrent access support"""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.index_manager = PgVectorIndexManager()
        self.cache = {}  # Simple in-memory cache
        self.cache_timeout = 3600  # 1 hour

    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using pgvector

        Args:
            query: Query text
            k: Number of results to return
            threshold: Similarity threshold (optional)
            filter_conditions: Additional filters to apply
            db: Database session

        Returns:
            List of search results with chunks and metadata
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.encode(query, normalize=True)

        # Use provided session or create new one
        if db:
            return await self._search_with_session(
                db, query_embedding, k, threshold, filter_conditions
            )

        async for session in get_async_db():
            return await self._search_with_session(
                session, query_embedding, k, threshold, filter_conditions
            )

    async def _search_with_session(
        self,
        db: AsyncSession,
        query_embedding: np.ndarray,
        k: int,
        threshold: Optional[float],
        filter_conditions: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute search with provided session"""
        try:
            # Optimize query parameters
            await self.index_manager.optimize_query_parameters(db)

            # Build base query using pgvector distance operator
            # Convert embedding to proper format for pgvector
            query_vector = f"[{','.join(map(str, query_embedding.tolist()))}]"

            query = select(
                DocumentChunk,
                func.cosine_distance(
                    DocumentChunk.embedding,
                    query_vector
                ).label('distance')
            )

            # Apply filters if provided
            if filter_conditions:
                if 'document_ids' in filter_conditions:
                    query = query.filter(
                        DocumentChunk.document_id.in_(filter_conditions['document_ids'])
                    )
                if 'is_active' in filter_conditions:
                    query = query.join(Document).filter(
                        Document.is_active == filter_conditions['is_active']
                    )

            # Apply similarity threshold if provided
            if threshold:
                query = query.filter(
                    func.cosine_distance(
                        DocumentChunk.embedding,
                        query_vector
                    ) <= (1 - threshold)  # Convert similarity to distance
                )

            # Order by distance and limit results
            query = query.order_by('distance').limit(k)

            # Execute query
            result = await db.execute(query)
            rows = result.all()

            # Format results
            search_results = []
            for chunk, distance in rows:
                similarity = 1 - distance  # Convert distance back to similarity

                search_results.append({
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'similarity': float(similarity),
                    'distance': float(distance),
                    'metadata': {
                        'page_number': chunk.page_number,
                        'section_title': chunk.section_title,
                    }
                })

            # Update document access counts
            if search_results:
                doc_ids = list(set(r['document_id'] for r in search_results))
                await db.execute(
                    text(
                        "UPDATE documents SET access_count = access_count + 1 "
                        "WHERE id IN :doc_ids"
                    ),
                    {"doc_ids": tuple(doc_ids)}
                )
                await db.commit()

            return search_results

        except Exception as e:
            logger.error(f"Error during pgvector search: {e}")
            return []

    async def add_document_embeddings(
        self,
        document_id: int,
        batch_size: int = 100,
        db: Optional[AsyncSession] = None
    ):
        """
        Add embeddings for document chunks

        Args:
            document_id: Document ID
            batch_size: Batch size for processing
            db: Database session
        """
        async def process_with_session(session: AsyncSession):
            # Get chunks without embeddings
            result = await session.execute(
                select(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.embedding.is_(None)
                )
            )
            chunks = result.scalars().all()

            if not chunks:
                logger.info(f"No chunks to embed for document {document_id}")
                return

            # Process in batches
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [chunk.content for chunk in batch]

                # Generate embeddings
                embeddings = self.embedding_service.encode(texts, normalize=True)

                # Update chunks
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding.tolist()
                    chunk.embedding_json = embedding.tolist()

                await session.commit()
                logger.info(f"Added embeddings for {len(batch)} chunks")

        if db:
            await process_with_session(db)
        else:
            async for session in get_async_db():
                await process_with_session(session)

    async def remove_document_embeddings(
        self,
        document_id: int,
        db: Optional[AsyncSession] = None
    ):
        """
        Remove embeddings for a document

        Args:
            document_id: Document ID
            db: Database session
        """
        async def process_with_session(session: AsyncSession):
            await session.execute(
                text(
                    "UPDATE document_chunks SET embedding = NULL, embedding_json = NULL "
                    "WHERE document_id = :doc_id"
                ),
                {"doc_id": document_id}
            )
            await session.commit()
            logger.info(f"Removed embeddings for document {document_id}")

        if db:
            await process_with_session(db)
        else:
            async for session in get_async_db():
                await process_with_session(session)

    async def update_index(self, db: Optional[AsyncSession] = None):
        """Update or create vector index"""
        if db:
            await self.index_manager.create_optimal_index(db)
        else:
            async for session in get_async_db():
                await self.index_manager.create_optimal_index(session)

    async def get_stats(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        async def get_with_session(session: AsyncSession):
            # Total documents
            doc_result = await session.execute(
                select(func.count(Document.id))
            )
            total_docs = doc_result.scalar()

            # Total chunks
            chunk_result = await session.execute(
                select(func.count(DocumentChunk.id))
            )
            total_chunks = chunk_result.scalar()

            # Chunks with embeddings
            embed_result = await session.execute(
                select(func.count(DocumentChunk.id)).filter(
                    DocumentChunk.embedding.isnot(None)
                )
            )
            chunks_with_embeddings = embed_result.scalar()

            return {
                'total_documents': total_docs,
                'total_chunks': total_chunks,
                'chunks_with_embeddings': chunks_with_embeddings,
                'embedding_coverage': (
                    chunks_with_embeddings / total_chunks * 100
                    if total_chunks > 0 else 0
                ),
                'service_type': 'pgvector',
                'embedding_model': self.embedding_service.model_name,
                'embedding_dimension': self.embedding_service.embedding_dim,
            }

        if db:
            return await get_with_session(db)
        else:
            async for session in get_async_db():
                return await get_with_session(session)

    def clear_cache(self):
        """Clear the search cache"""
        self.cache.clear()
        logger.info("PgVector search cache cleared")


# Synchronous version for Celery tasks
class PgVectorSearchServiceSync:
    """Synchronous version of PgVector service for Celery tasks"""

    def __init__(self):
        self.embedding_service = get_embedding_service()

    def add_document_embeddings(self, document_id: int, batch_size: int = 100):
        """Synchronous version for adding embeddings"""
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            # Get chunks without embeddings
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.embedding.is_(None)
            ).all()

            if not chunks:
                logger.info(f"No chunks to embed for document {document_id}")
                return

            # Process in batches
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [chunk.content for chunk in batch]

                # Generate embeddings
                embeddings = self.embedding_service.encode(texts, normalize=True)

                # Update chunks
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding.tolist()
                    chunk.embedding_json = embedding.tolist()

                db.commit()
                logger.info(f"Added embeddings for {len(batch)} chunks")