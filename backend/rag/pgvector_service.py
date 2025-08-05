"""
PgVector Search Service for Knight Agent
Production-ready implementation with concurrent access support
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction, connection
from django.core.cache import cache
from pgvector.django import CosineDistance, L2Distance, MaxInnerProduct
import logging

logger = logging.getLogger(__name__)


class PgVectorIndexManager:
    """Manages pgvector indexes for optimal performance"""
    
    @staticmethod
    def create_optimal_index(table_name='documents_documentchunk', field_name='embedding'):
        """Create optimal index based on data size"""
        try:
            with connection.cursor() as cursor:
                # Check current row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {field_name} IS NOT NULL")
                row_count = cursor.fetchone()[0]
                
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
                
                cursor.execute(index_sql)
                logger.info("Index created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    @staticmethod
    def optimize_query_parameters():
        """Set optimal query parameters for similarity search"""
        try:
            with connection.cursor() as cursor:
                # For HNSW indexes
                cursor.execute("SET hnsw.ef_search = 64")  # Higher for better recall
                
                # For IVFFlat indexes
                cursor.execute("SET ivfflat.probes = 10")  # sqrt(lists) approximately
                
                logger.debug("Query parameters optimized")
        except Exception as e:
            logger.warning(f"Could not optimize query parameters: {e}")


class PgVectorSearchService:
    """Production-ready pgvector search service with concurrent access support"""
    
    def __init__(self):
        self.embedding_service = None
        self.index_manager = PgVectorIndexManager()
        self.cache_timeout = 3600  # 1 hour cache
    
    def _get_embedding_service(self):
        """Lazy load embedding service to avoid circular imports"""
        if self.embedding_service is None:
            from .services import EmbeddingService
            self.embedding_service = EmbeddingService()
        return self.embedding_service
    
    @transaction.atomic
    def add_document_embeddings(self, document, batch_size: int = 100):
        """Batch insert embeddings with optimal performance"""
        from documents.models import DocumentChunk
        
        chunks = document.chunks.filter(embedding__isnull=True)
        
        if not chunks.exists():
            logger.info(f"No chunks to embed for document {document.id}")
            return
        
        embedding_service = self._get_embedding_service()
        chunks_list = list(chunks)
        
        logger.info(f"Processing {len(chunks_list)} chunks for document {document.id}")
        
        # Process in batches to avoid memory issues
        for i in range(0, len(chunks_list), batch_size):
            batch = chunks_list[i:i + batch_size]
            texts = [chunk.content for chunk in batch]
            
            # Generate embeddings
            embeddings = embedding_service.encode_texts(texts)
            
            # Prepare bulk update
            updates = []
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding.tolist()
                updates.append(chunk)
            
            # Bulk update with pgvector
            DocumentChunk.objects.bulk_update(updates, ['embedding'], batch_size=batch_size)
            
            logger.debug(f"Updated batch {i//batch_size + 1} of {len(chunks_list)//batch_size + 1}")
        
        logger.info(f"Successfully embedded all chunks for document {document.id}")
    
    def search(
        self, 
        query: str, 
        k: int = 5, 
        distance_threshold: float = 0.8,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Optimized similarity search with pgvector"""
        from documents.models import DocumentChunk
        
        if not query.strip():
            return []
        
        # Check cache first
        cache_key = f"pgvector_search:{query}:{k}:{distance_threshold}:{document_ids}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached_results
        
        # Optimize query parameters
        self.index_manager.optimize_query_parameters()
        
        # Generate query embedding
        embedding_service = self._get_embedding_service()
        query_embedding = embedding_service.encode_single_text(query)
        
        # Build query with filters
        queryset = DocumentChunk.objects.filter(
            embedding__isnull=False,
            document__status='processed',
            document__is_active=True
        ).select_related('document')
        
        # Filter by documents if specified
        if document_ids:
            queryset = queryset.filter(document_id__in=document_ids)
        
        # Annotate with similarity distance
        queryset = queryset.annotate(
            similarity_distance=CosineDistance('embedding', query_embedding.tolist())
        ).filter(
            similarity_distance__lt=distance_threshold  # Filter by threshold
        ).order_by('similarity_distance')[:k]
        
        # Convert to result format
        results = []
        for chunk in queryset:
            similarity_score = 1.0 - chunk.similarity_distance  # Convert distance to similarity
            results.append({
                'document_id': chunk.document.id,
                'document_title': chunk.document.title,
                'chunk_id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'score': float(similarity_score),
                'search_type': 'pgvector_semantic',
                'page_number': chunk.page_number,
                'section_title': chunk.section_title
            })
        
        # Cache results
        cache.set(cache_key, results, self.cache_timeout)
        
        logger.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results
    
    def hybrid_search_with_sql_filters(
        self, 
        query: str, 
        k: int = 5,
        document_types: Optional[List[str]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining pgvector similarity with SQL filters and BM25"""
        
        if not query.strip():
            return []
        
        embedding_service = self._get_embedding_service()
        query_embedding = embedding_service.encode_single_text(query)
        
        # Base query with filters
        base_query = """
        SELECT 
            dc.id as chunk_id,
            dc.document_id,
            dc.chunk_index,
            dc.content,
            dc.page_number,
            dc.section_title,
            d.title as document_title,
            d.file_type,
            d.uploaded_at,
            (1 - (dc.embedding <=> %s::vector)) as semantic_score,
            ts_rank_cd(
                to_tsvector('portuguese', dc.content), 
                plainto_tsquery('portuguese', %s)
            ) as bm25_score
        FROM documents_documentchunk dc
        JOIN documents_document d ON dc.document_id = d.id
        WHERE dc.embedding IS NOT NULL 
        AND d.status = 'processed' 
        AND d.is_active = true
        """
        
        params = [query_embedding.tolist(), query]
        
        # Add filters
        if document_types:
            placeholders = ','.join(['%s'] * len(document_types))
            base_query += f" AND d.file_type IN ({placeholders})"
            params.extend(document_types)
        
        if date_range:
            base_query += " AND d.uploaded_at BETWEEN %s AND %s"
            params.extend(date_range)
        
        # Combine scores and order
        base_query += f"""
        ORDER BY (
            semantic_score * {semantic_weight} + 
            COALESCE(bm25_score, 0) * {1 - semantic_weight}
        ) DESC
        LIMIT %s
        """
        params.append(k)
        
        results = []
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)
            columns = [col[0] for col in cursor.description]
            
            for row in cursor.fetchall():
                result_dict = dict(zip(columns, row))
                combined_score = float(
                    result_dict['semantic_score'] * semantic_weight + 
                    (result_dict['bm25_score'] or 0) * (1 - semantic_weight)
                )
                
                results.append({
                    'document_id': result_dict['document_id'],
                    'document_title': result_dict['document_title'],
                    'chunk_id': result_dict['chunk_id'],
                    'chunk_index': result_dict['chunk_index'],
                    'content': result_dict['content'],
                    'score': float(result_dict['semantic_score']),
                    'combined_score': combined_score,
                    'search_type': 'pgvector_hybrid',
                    'page_number': result_dict['page_number'],
                    'section_title': result_dict['section_title']
                })
        
        logger.info(f"Hybrid search found {len(results)} results for query: {query[:50]}...")
        return results
    
    @transaction.atomic
    def remove_document_embeddings(self, document_id: int):
        """Remove embeddings for a specific document - concurrent safe"""
        from documents.models import DocumentChunk
        
        deleted_count = DocumentChunk.objects.filter(
            document_id=document_id
        ).update(embedding=None)
        
        # Clear cache for this document
        cache_pattern = f"pgvector_search:*:{document_id}*"
        cache.delete_pattern(cache_pattern)
        
        logger.info(f"Removed {deleted_count} embeddings for document {document_id}")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(embedding) as embedded_chunks,
                    COUNT(DISTINCT document_id) as total_documents,
                    pg_size_pretty(pg_total_relation_size('documents_documentchunk')) as table_size
                FROM documents_documentchunk
            """)
            
            row = cursor.fetchone()
            
            # Get index statistics
            cursor.execute("""
                SELECT 
                    indexname, 
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                FROM pg_indexes 
                WHERE tablename = 'documents_documentchunk' 
                AND indexname LIKE '%embedding%'
            """)
            
            index_info = cursor.fetchall()
            
            return {
                'total_chunks': row[0],
                'embedded_chunks': row[1], 
                'total_documents': row[2],
                'table_size': row[3],
                'embedding_coverage': round((row[1] / row[0] * 100) if row[0] > 0 else 0, 2),
                'indexes': [{'name': idx[0], 'size': idx[1]} for idx in index_info]
            }
    
    def migrate_from_faiss(self, batch_size: int = 1000):
        """Migrate existing embeddings from FAISS/JSON to pgvector"""
        from documents.models import DocumentChunk
        
        # Count chunks with JSON embeddings but no vector embeddings
        chunks_to_migrate = DocumentChunk.objects.filter(
            embedding_json__isnull=False,
            embedding__isnull=True
        )
        
        total_chunks = chunks_to_migrate.count()
        logger.info(f"Found {total_chunks} chunks to migrate from FAISS to pgvector")
        
        if total_chunks == 0:
            logger.info("No chunks to migrate")
            return 0
        
        migrated = 0
        
        # Process in batches
        for start in range(0, total_chunks, batch_size):
            with transaction.atomic():
                batch = list(chunks_to_migrate[start:start + batch_size])
                updates = []
                
                for chunk in batch:
                    if chunk.embedding_json:
                        # Convert JSON list to vector
                        chunk.embedding = chunk.embedding_json
                        updates.append(chunk)
                
                if updates:
                    DocumentChunk.objects.bulk_update(
                        updates, ['embedding'], batch_size=batch_size
                    )
                    migrated += len(updates)
                    
                    logger.info(f"Migrated {migrated}/{total_chunks} chunks")
        
        # Create index after migration
        if migrated > 0:
            logger.info("Creating optimal index for migrated data")
            self.index_manager.create_optimal_index()
        
        return migrated