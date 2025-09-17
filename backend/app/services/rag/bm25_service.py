"""
BM25 Keyword Search Service for FastAPI
Optimized for Portuguese text
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import numpy as np

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# Session import removed - using only AsyncSession for FastAPI compatibility

from app.core.database import get_async_db
from app.models import Document, DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)


class BM25SearchService:
    """BM25 keyword search service optimized for Portuguese"""

    def __init__(self):
        self.bm25_index = None
        self.chunk_ids = []
        self.chunk_contents = []
        self.document_map = {}
        self.portuguese_stopwords = self._load_portuguese_stopwords()

    def _load_portuguese_stopwords(self) -> set:
        """Load Portuguese stopwords"""
        # Common Portuguese stopwords
        stopwords = {
            'a', 'o', 'e', 'é', 'de', 'da', 'do', 'em', 'para', 'com', 'por',
            'que', 'um', 'uma', 'os', 'as', 'dos', 'das', 'na', 'no', 'nas', 'nos',
            'ao', 'à', 'pela', 'pelo', 'pelas', 'pelos', 'sem', 'sob', 'sobre',
            'seu', 'sua', 'seus', 'suas', 'este', 'esta', 'estes', 'estas',
            'esse', 'essa', 'esses', 'essas', 'aquele', 'aquela', 'aqueles', 'aquelas',
            'isto', 'isso', 'aquilo', 'eu', 'tu', 'ele', 'ela', 'nós', 'vós',
            'eles', 'elas', 'me', 'te', 'se', 'lhe', 'nos', 'vos', 'lhes',
            'muito', 'muita', 'muitos', 'muitas', 'pouco', 'pouca', 'poucos', 'poucas',
            'mais', 'menos', 'bem', 'mal', 'assim', 'também', 'já', 'ainda',
            'quando', 'onde', 'como', 'porque', 'porquê', 'qual', 'quais',
            'quem', 'quanto', 'quanta', 'quantos', 'quantas'
        }
        return stopwords

    def _preprocess_text(self, text: str) -> List[str]:
        """
        Preprocess text for BM25

        Args:
            text: Input text

        Returns:
            List of processed tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep Portuguese accents
        text = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûç]', ' ', text)

        # Tokenize
        tokens = text.split()

        # Remove stopwords
        tokens = [t for t in tokens if t not in self.portuguese_stopwords and len(t) > 2]

        return tokens

    async def build_index(self, db: Optional[AsyncSession] = None):
        """
        Build or rebuild BM25 index from all document chunks

        Args:
            db: Database session
        """
        async def build_with_session(session: AsyncSession):
            # Get all active document chunks
            result = await session.execute(
                select(DocumentChunk, Document).join(
                    Document,
                    DocumentChunk.document_id == Document.id
                ).filter(
                    Document.is_active == True
                )
            )
            rows = result.all()

            if not rows:
                logger.warning("No active documents found for BM25 index")
                return

            # Reset index data
            self.chunk_ids = []
            self.chunk_contents = []
            self.document_map = {}
            tokenized_corpus = []

            for chunk, document in rows:
                self.chunk_ids.append(chunk.id)
                self.chunk_contents.append(chunk.content)
                self.document_map[chunk.id] = {
                    'document_id': document.id,
                    'document_title': document.title,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title,
                }

                # Tokenize and add to corpus
                tokens = self._preprocess_text(chunk.content)
                tokenized_corpus.append(tokens)

            # Build BM25 index
            self.bm25_index = BM25Okapi(tokenized_corpus)

            logger.info(f"BM25 index built with {len(self.chunk_ids)} chunks")

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
        filter_document_ids: Optional[List[int]] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search

        Args:
            query: Search query
            k: Number of results to return
            threshold: Score threshold (optional)
            filter_document_ids: Filter by specific document IDs
            db: Database session

        Returns:
            List of search results
        """
        # Build index if not available
        if self.bm25_index is None:
            await self.build_index(db)

        if self.bm25_index is None:
            logger.error("Failed to build BM25 index")
            return []

        # Preprocess query
        query_tokens = self._preprocess_text(query)

        if not query_tokens:
            logger.warning("Query resulted in no tokens after preprocessing")
            return []

        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)

        # Create results with scores
        scored_results = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only include non-zero scores
                chunk_id = self.chunk_ids[idx]

                # Apply document filter if provided
                if filter_document_ids:
                    doc_id = self.document_map[chunk_id]['document_id']
                    if doc_id not in filter_document_ids:
                        continue

                # Apply threshold if provided
                if threshold and score < threshold:
                    continue

                scored_results.append({
                    'chunk_id': chunk_id,
                    'score': float(score),
                    'content': self.chunk_contents[idx],
                    **self.document_map[chunk_id]
                })

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x['score'], reverse=True)

        # Return top k results
        return scored_results[:k]

    async def search_with_highlighting(
        self,
        query: str,
        k: int = 5,
        context_size: int = 50,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with keyword highlighting

        Args:
            query: Search query
            k: Number of results
            context_size: Characters of context around highlight
            db: Database session

        Returns:
            Search results with highlighted snippets
        """
        results = await self.search(query, k, db=db)

        # Add highlighting to results
        query_tokens = self._preprocess_text(query)

        for result in results:
            content = result['content']
            highlights = []

            # Find occurrences of query tokens
            for token in query_tokens:
                pattern = re.compile(r'\b' + re.escape(token) + r'\b', re.IGNORECASE)
                matches = pattern.finditer(content)

                for match in matches:
                    start = max(0, match.start() - context_size)
                    end = min(len(content), match.end() + context_size)

                    snippet = content[start:end]
                    if start > 0:
                        snippet = '...' + snippet
                    if end < len(content):
                        snippet = snippet + '...'

                    # Highlight the matched token
                    highlighted = pattern.sub(f'**{match.group()}**', snippet)
                    highlights.append(highlighted)

            result['highlights'] = highlights[:3]  # Limit to 3 highlights

        return results

    def get_term_frequencies(self, query: str) -> Dict[str, int]:
        """
        Get term frequencies for query terms in the corpus

        Args:
            query: Search query

        Returns:
            Dictionary of term frequencies
        """
        query_tokens = self._preprocess_text(query)
        frequencies = {}

        for token in query_tokens:
            count = 0
            for content in self.chunk_contents:
                content_tokens = self._preprocess_text(content)
                count += content_tokens.count(token)
            frequencies[token] = count

        return frequencies

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the BM25 index"""
        if self.bm25_index is None:
            return {
                'status': 'not_initialized',
                'indexed_chunks': 0,
                'unique_documents': 0,
            }

        unique_docs = len(set(
            info['document_id'] for info in self.document_map.values()
        ))

        # Calculate vocabulary size
        vocab_size = 0
        if hasattr(self.bm25_index, 'idf'):
            vocab_size = len(self.bm25_index.idf)

        return {
            'status': 'ready',
            'indexed_chunks': len(self.chunk_ids),
            'unique_documents': unique_docs,
            'vocabulary_size': vocab_size,
            'service_type': 'bm25',
        }

    async def update_document(
        self,
        document_id: int,
        db: Optional[AsyncSession] = None
    ):
        """
        Update index for a specific document

        Args:
            document_id: Document ID to update
            db: Database session
        """
        # For now, rebuild entire index
        # In production, could implement incremental updates
        await self.build_index(db)

    async def remove_document(self, document_id: int):
        """
        Remove document from index

        Args:
            document_id: Document ID to remove
        """
        # For now, rebuild entire index
        # In production, could implement incremental removal
        await self.build_index()


# Synchronous version for compatibility
class BM25SearchServiceSync:
    """Synchronous version of BM25 service"""

    def __init__(self):
        self.service = BM25SearchService()

    def build_index(self):
        """Build index synchronously"""
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            # Get all active chunks
            chunks = db.query(DocumentChunk, Document).join(
                Document,
                DocumentChunk.document_id == Document.id
            ).filter(
                Document.is_active == True
            ).all()

            if not chunks:
                logger.warning("No active documents found for BM25 index")
                return

            # Reset index data
            self.service.chunk_ids = []
            self.service.chunk_contents = []
            self.service.document_map = {}
            tokenized_corpus = []

            for chunk, document in chunks:
                self.service.chunk_ids.append(chunk.id)
                self.service.chunk_contents.append(chunk.content)
                self.service.document_map[chunk.id] = {
                    'document_id': document.id,
                    'document_title': document.title,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section_title': chunk.section_title,
                }

                # Tokenize and add to corpus
                tokens = self.service._preprocess_text(chunk.content)
                tokenized_corpus.append(tokens)

            # Build BM25 index
            self.service.bm25_index = BM25Okapi(tokenized_corpus)

            logger.info(f"BM25 index built with {len(self.service.chunk_ids)} chunks")

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Synchronous search"""
        if self.service.bm25_index is None:
            self.build_index()

        if self.service.bm25_index is None:
            return []

        query_tokens = self.service._preprocess_text(query)
        if not query_tokens:
            return []

        scores = self.service.bm25_index.get_scores(query_tokens)

        scored_results = []
        for idx, score in enumerate(scores):
            if score > 0:
                chunk_id = self.service.chunk_ids[idx]
                scored_results.append({
                    'chunk_id': chunk_id,
                    'score': float(score),
                    'content': self.service.chunk_contents[idx],
                    **self.service.document_map[chunk_id]
                })

        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results[:k]