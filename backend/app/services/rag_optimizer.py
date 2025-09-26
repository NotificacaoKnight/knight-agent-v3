"""
RAG Performance Optimizer
Implements batch processing, parallelization, and query optimization for RAG
"""
import asyncio
import hashlib
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import time

from app.services.embedding_service import EmbeddingService
from app.services.cache_service import cache_service, embedding_cache, cache_l2

logger = logging.getLogger(__name__)

class RAGOptimizer:
    """
    Performance optimizations for RAG system
    """

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.cache = cache_service
        self.embedding_cache = embedding_cache

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings in batches with caching

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            use_cache: Whether to use caching

        Returns:
            List of embedding vectors
        """
        embeddings = []
        texts_to_compute = []
        text_to_index = {}

        # Check cache for each text
        if use_cache:
            for i, text in enumerate(texts):
                cached_embedding = await self.embedding_cache.get_embedding(text)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                else:
                    texts_to_compute.append(text)
                    text_to_index[text] = i
        else:
            texts_to_compute = texts

        # Process uncached texts in batches
        if texts_to_compute:
            logger.info(f"Computing {len(texts_to_compute)} new embeddings in batches of {batch_size}")

            for i in range(0, len(texts_to_compute), batch_size):
                batch = texts_to_compute[i:i + batch_size]

                # Generate embeddings for batch
                batch_embeddings = self.embedding_service.encode_texts(batch)

                # Cache each embedding
                if use_cache:
                    for text, embedding in zip(batch, batch_embeddings):
                        await self.embedding_cache.set_embedding(text, embedding)

                embeddings.extend(batch_embeddings)

        return embeddings

    async def parallel_process_chunks(
        self,
        chunks: List[str],
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Process document chunks in parallel

        Args:
            chunks: List of text chunks
            max_workers: Maximum parallel workers

        Returns:
            List of processed chunks with metadata
        """
        async def process_single_chunk(chunk: str, index: int) -> Dict[str, Any]:
            """Process a single chunk"""
            try:
                # Generate embedding
                embedding = await self.embedding_cache.get_or_compute(
                    chunk,
                    lambda t: self.embedding_service.encode_texts([t])[0]
                )

                # Extract metadata (simplified)
                word_count = len(chunk.split())
                char_count = len(chunk)

                return {
                    'index': index,
                    'text': chunk,
                    'embedding': embedding,
                    'metadata': {
                        'word_count': word_count,
                        'char_count': char_count
                    }
                }
            except Exception as e:
                logger.error(f"Error processing chunk {index}: {e}")
                return None

        # Create tasks for parallel processing
        tasks = []
        for i, chunk in enumerate(chunks):
            if i < max_workers:
                # Start immediately
                task = asyncio.create_task(process_single_chunk(chunk, i))
            else:
                # Wait for a slot
                await asyncio.sleep(0)  # Yield control
                task = asyncio.create_task(process_single_chunk(chunk, i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        # Filter out failed chunks
        processed_chunks = [r for r in results if r is not None]

        logger.info(f"Processed {len(processed_chunks)}/{len(chunks)} chunks successfully")
        return processed_chunks

    @cache_l2(prefix="smart_search", ttl=1800)
    async def smart_search_with_early_stopping(
        self,
        query: str,
        search_func,
        threshold: float = 0.85,
        initial_k: int = 3,
        extended_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Smart search with early stopping for high-quality matches

        Args:
            query: Search query
            search_func: Function to perform search
            threshold: Score threshold for early stopping
            initial_k: Initial number of results to fetch
            extended_k: Extended number of results if needed

        Returns:
            Search results
        """
        # First, do a quick search
        start_time = time.time()
        initial_results = await search_func(query, k=initial_k)

        # Check if we have high-quality results
        if initial_results and any(r.get('score', 0) > threshold for r in initial_results):
            logger.info(f"Early stopping triggered - found high-quality results in {time.time() - start_time:.2f}s")
            return initial_results

        # No high-quality results, do extended search
        logger.info("Extending search for better results...")
        extended_results = await search_func(query, k=extended_k)

        logger.info(f"Extended search completed in {time.time() - start_time:.2f}s")
        return extended_results

    def quantize_vectors(
        self,
        vectors: np.ndarray,
        precision: str = 'int8'
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Quantize vectors to reduce memory usage

        Args:
            vectors: Vectors to quantize
            precision: Target precision ('int8' or 'int16')

        Returns:
            Quantized vectors and quantization parameters
        """
        if precision == 'int8':
            # Quantize to int8 (1 byte per value)
            min_val = vectors.min()
            max_val = vectors.max()

            # Scale to int8 range
            scale = 127.0 / max(abs(min_val), abs(max_val))
            quantized = (vectors * scale).astype(np.int8)

            params = {
                'scale': scale,
                'min_val': min_val,
                'max_val': max_val,
                'precision': 'int8'
            }
        elif precision == 'int16':
            # Quantize to int16 (2 bytes per value)
            min_val = vectors.min()
            max_val = vectors.max()

            scale = 32767.0 / max(abs(min_val), abs(max_val))
            quantized = (vectors * scale).astype(np.int16)

            params = {
                'scale': scale,
                'min_val': min_val,
                'max_val': max_val,
                'precision': 'int16'
            }
        else:
            # No quantization
            return vectors, {'precision': 'float32'}

        logger.info(f"Quantized vectors from {vectors.dtype} to {precision}, "
                   f"reduced size by {(1 - quantized.nbytes / vectors.nbytes) * 100:.1f}%")

        return quantized, params

    def dequantize_vectors(
        self,
        quantized: np.ndarray,
        params: Dict[str, float]
    ) -> np.ndarray:
        """
        Dequantize vectors back to float32

        Args:
            quantized: Quantized vectors
            params: Quantization parameters

        Returns:
            Original vectors (approximately)
        """
        if params.get('precision') in ['int8', 'int16']:
            scale = params['scale']
            vectors = quantized.astype(np.float32) / scale
        else:
            vectors = quantized

        return vectors

    @lru_cache(maxsize=1000)
    def get_popular_query_cache(self, query_pattern: str) -> Optional[List[Dict]]:
        """
        Cache for popular query patterns

        Args:
            query_pattern: Query pattern to check

        Returns:
            Cached results if available
        """
        # Define popular patterns and their cached results
        popular_patterns = {
            'como fazer': 'how_to',
            'o que é': 'what_is',
            'política de': 'policy',
            'procedimento': 'procedure',
            'manual': 'manual',
            'documento': 'document'
        }

        for pattern, cache_key in popular_patterns.items():
            if pattern in query_pattern.lower():
                logger.debug(f"Popular query pattern detected: {pattern}")
                return cache_key

        return None

    async def optimize_context_selection(
        self,
        documents: List[Dict[str, Any]],
        max_tokens: int = 8000,
        strategy: str = 'relevance'
    ) -> List[Dict[str, Any]]:
        """
        Optimize document selection for context window

        Args:
            documents: List of documents with scores
            max_tokens: Maximum context tokens
            strategy: Selection strategy ('relevance', 'diversity', 'coverage')

        Returns:
            Optimized list of documents
        """
        selected_docs = []
        current_tokens = 0

        if strategy == 'relevance':
            # Select by relevance score
            sorted_docs = sorted(documents, key=lambda x: x.get('score', 0), reverse=True)
        elif strategy == 'diversity':
            # Select diverse documents (simplified - could use clustering)
            sorted_docs = documents
            # TODO: Implement diversity-based selection
        else:  # coverage
            # Select to maximize topic coverage
            sorted_docs = documents
            # TODO: Implement coverage-based selection

        for doc in sorted_docs:
            # Estimate token count (rough approximation)
            doc_tokens = len(doc.get('text', '').split()) * 1.3

            if current_tokens + doc_tokens <= max_tokens:
                selected_docs.append(doc)
                current_tokens += doc_tokens
            else:
                # Check if we can add a truncated version
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # Minimum useful size
                    # Truncate document
                    words_to_keep = int(remaining_tokens / 1.3)
                    truncated_text = ' '.join(doc.get('text', '').split()[:words_to_keep])
                    doc_copy = doc.copy()
                    doc_copy['text'] = truncated_text + '...'
                    doc_copy['truncated'] = True
                    selected_docs.append(doc_copy)
                break

        logger.info(f"Selected {len(selected_docs)}/{len(documents)} documents "
                   f"using {current_tokens}/{max_tokens} tokens")

        return selected_docs

class QueryOptimizer:
    """
    Optimize search queries for better results
    """

    def __init__(self):
        self.common_expansions = {
            'rh': 'recursos humanos',
            'ti': 'tecnologia da informação',
            'doc': 'documento',
            'proc': 'procedimento',
            'pol': 'política'
        }

    def expand_abbreviations(self, query: str) -> str:
        """
        Expand common abbreviations in query

        Args:
            query: Original query

        Returns:
            Query with expanded abbreviations
        """
        query_lower = query.lower()
        expanded = query

        for abbr, full in self.common_expansions.items():
            if abbr in query_lower.split():
                expanded = expanded.replace(abbr, full)
                expanded = expanded.replace(abbr.upper(), full)

        if expanded != query:
            logger.debug(f"Expanded query: '{query}' -> '{expanded}'")

        return expanded

    def remove_stopwords(self, query: str) -> str:
        """
        Remove Portuguese stopwords from query

        Args:
            query: Original query

        Returns:
            Query without stopwords
        """
        # Portuguese stopwords (simplified list)
        stopwords = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'da', 'do', 'no', 'na',
            'em', 'para', 'com', 'por', 'que', 'e', 'é', 'ou', 'mas', 'se'
        }

        words = query.split()
        filtered = [w for w in words if w.lower() not in stopwords]

        return ' '.join(filtered) if filtered else query

    def optimize_query(self, query: str) -> str:
        """
        Apply all query optimizations

        Args:
            query: Original query

        Returns:
            Optimized query
        """
        # Expand abbreviations
        query = self.expand_abbreviations(query)

        # Remove extra spaces
        query = ' '.join(query.split())

        return query

# Global optimizer instances
rag_optimizer = RAGOptimizer()
query_optimizer = QueryOptimizer()