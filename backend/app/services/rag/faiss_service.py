"""
FAISS Vector Search Service for FastAPI
In-memory fallback for vector similarity search
"""
import os
import pickle
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

import faiss
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


class FAISSSearchService:
    """FAISS in-memory vector search service"""

    def __init__(self, index_path: str = None):
        """
        Initialize FAISS service

        Args:
            index_path: Path to save/load FAISS index
        """
        self.index_path = index_path or "faiss_index.pkl"
        self.index = None
        self.chunk_map = {}  # Maps index position to chunk info
        self.embedding_service = get_embedding_service()
        self.dimension = self.embedding_service.embedding_dim

        # Load existing index if available
        self.load_index()

    def load_index(self):
        """Load FAISS index from disk if exists"""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'rb') as f:
                    data = pickle.load(f)
                    self.index = data['index']
                    self.chunk_map = data['chunk_map']
                logger.info(f"FAISS index loaded from {self.index_path}")
            except Exception as e:
                logger.warning(f"Could not load FAISS index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index"""
        # Using IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunk_map = {}
        logger.info(f"Created new FAISS index with dimension {self.dimension}")

    def save_index(self):
        """Save FAISS index to disk"""
        try:
            data = {
                'index': self.index,
                'chunk_map': self.chunk_map
            }
            with open(self.index_path, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"FAISS index saved to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    async def build_index(self, db: Optional[AsyncSession] = None):
        """
        Build FAISS index from all document chunks

        Args:
            db: Database session
        """
        async def build_with_session(session: AsyncSession):
            # Get all chunks with embeddings
            result = await session.execute(
                select(DocumentChunk, Document).join(
                    Document,
                    DocumentChunk.document_id == Document.id
                ).filter(
                    Document.is_active == True,
                    DocumentChunk.embedding.isnot(None)
                )
            )
            rows = result.all()

            if not rows:
                logger.warning("No chunks with embeddings found")
                return

            # Reset index
            self._create_new_index()

            # Collect embeddings and metadata
            embeddings = []
            for idx, (chunk, document) in enumerate(rows):
                # Get embedding from JSON field (fallback)
                if chunk.embedding_json:
                    embedding = np.array(chunk.embedding_json, dtype=np.float32)
                else:
                    # Generate embedding if missing
                    embedding = self.embedding_service.encode(chunk.content, normalize=True)

                embeddings.append(embedding)

                # Store chunk metadata
                self.chunk_map[idx] = {
                    'chunk_id': chunk.id,
                    'document_id': document.id,
                    'document_title': document.title,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title,
                }

            # Add to index
            embeddings_array = np.array(embeddings, dtype=np.float32)
            self.index.add(embeddings_array)

            # Save index
            self.save_index()

            logger.info(f"FAISS index built with {len(embeddings)} vectors")

        if db:
            await build_with_session(db)
        else:
            async for session in get_async_db():
                await build_with_session(session)

    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using FAISS index

        Args:
            query: Query text
            k: Number of results
            threshold: Similarity threshold
            filter_conditions: Additional filters

        Returns:
            Search results
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        # Generate query embedding
        query_embedding = self.embedding_service.encode(query, normalize=True)
        query_embedding = np.array([query_embedding], dtype=np.float32)

        # Search
        distances, indices = self.index.search(query_embedding, min(k * 2, self.index.ntotal))

        # Process results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue

            # Apply threshold if provided
            if threshold and dist < threshold:
                continue

            chunk_info = self.chunk_map.get(idx)
            if not chunk_info:
                continue

            # Apply filters
            if filter_conditions:
                if 'document_ids' in filter_conditions:
                    if chunk_info['document_id'] not in filter_conditions['document_ids']:
                        continue

            results.append({
                **chunk_info,
                'similarity': float(dist),  # Inner product score
                'distance': float(1 - dist),  # Convert to distance
            })

        return results[:k]

    async def add_document_embeddings(self, document_id: int):
        """
        Add document chunks to FAISS index

        Args:
            document_id: Document ID
        """
        async for db in get_async_db():
            # Get chunks
            result = await db.execute(
                select(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.embedding.isnot(None)
                )
            )
            chunks = result.scalars().all()

            if not chunks:
                logger.warning(f"No chunks with embeddings for document {document_id}")
                return

            # Add each chunk
            for chunk in chunks:
                # Get embedding
                if chunk.embedding_json:
                    embedding = np.array(chunk.embedding_json, dtype=np.float32)
                else:
                    embedding = self.embedding_service.encode(chunk.content, normalize=True)

                # Add to index
                embedding = np.array([embedding], dtype=np.float32)
                self.index.add(embedding)

                # Update chunk map
                idx = self.index.ntotal - 1
                self.chunk_map[idx] = {
                    'chunk_id': chunk.id,
                    'document_id': document_id,
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title,
                }

            # Save index
            self.save_index()
            logger.info(f"Added {len(chunks)} chunks to FAISS index")

    async def remove_document(self, document_id: int):
        """
        Remove document from index
        Note: FAISS doesn't support deletion, so we rebuild

        Args:
            document_id: Document ID to remove
        """
        # Filter out chunks from this document
        new_chunk_map = {}
        removed_indices = []

        for idx, info in self.chunk_map.items():
            if info['document_id'] != document_id:
                new_chunk_map[len(new_chunk_map)] = info
            else:
                removed_indices.append(idx)

        if removed_indices:
            # Rebuild index without removed chunks
            logger.info(f"Rebuilding FAISS index after removing document {document_id}")
            await self.build_index()

    async def get_stats(self) -> Dict[str, Any]:
        """Get FAISS index statistics"""
        if self.index is None:
            return {
                'status': 'not_initialized',
                'total_vectors': 0,
                'dimension': self.dimension,
                'service_type': 'faiss',
            }

        unique_docs = len(set(
            info['document_id'] for info in self.chunk_map.values()
        ))

        return {
            'status': 'ready',
            'total_vectors': self.index.ntotal,
            'unique_documents': unique_docs,
            'dimension': self.dimension,
            'index_size_mb': os.path.getsize(self.index_path) / 1024 / 1024 if os.path.exists(self.index_path) else 0,
            'service_type': 'faiss',
            'embedding_model': self.embedding_service.model_name,
        }

    def clear_cache(self):
        """Clear any caches (FAISS doesn't use cache)"""
        pass