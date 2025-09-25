"""
Embedding Service using BGE-M3 model
Generates embeddings for document chunks
"""
import logging
import numpy as np
from typing import List, Optional, Union, Dict, Any
from functools import lru_cache
import torch

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using BGE-M3
    Optimized for multilingual text (Portuguese + English)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
        use_cache: bool = True
    ):
        """
        Initialize embedding service

        Args:
            model_name: Model to use for embeddings
            device: Device to use (cuda/cpu/auto)
            batch_size: Batch size for encoding
            max_length: Maximum sequence length
            use_cache: Whether to cache embeddings
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_cache = use_cache

        # Determine device
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
            logger.info("Using CUDA for embeddings")
        else:
            self.device = "cpu"
            logger.info("Using CPU for embeddings")

        # Initialize model
        self._initialize_model()

        # Cache for embeddings
        if self.use_cache:
            self._cache = {}

    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")

            # Load model using HuggingFace cache directory
            self.model = SentenceTransformer(self.model_name, device=self.device)

            # Set max sequence length
            self.model.max_seq_length = self.max_length

            # Get embedding dimension
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            logger.warning("Falling back to basic model")

            # Fallback to a simpler model
            try:
                self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Fallback model loaded. Dimension: {self.embedding_dim}")
            except Exception as fallback_error:
                logger.error(f"Failed to load fallback model: {fallback_error}")
                raise

    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode texts to embeddings

        Args:
            texts: Text or list of texts to encode
            normalize: Whether to normalize embeddings
            show_progress: Whether to show progress bar

        Returns:
            Numpy array of embeddings
        """
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False

        # Check cache
        if self.use_cache:
            cached_embeddings = []
            texts_to_encode = []
            cache_indices = []

            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    cached_embeddings.append(self._cache[cache_key])
                else:
                    texts_to_encode.append(text)
                    cache_indices.append(i)

            # If all texts are cached
            if not texts_to_encode:
                embeddings = np.array(cached_embeddings)
                return embeddings[0] if single_text else embeddings

        else:
            texts_to_encode = texts
            cache_indices = list(range(len(texts)))

        # Encode texts
        if texts_to_encode:
            try:
                new_embeddings = self.model.encode(
                    texts_to_encode,
                    batch_size=self.batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True
                )

                # Add to cache
                if self.use_cache:
                    for text, embedding in zip(texts_to_encode, new_embeddings):
                        cache_key = self._get_cache_key(text)
                        self._cache[cache_key] = embedding

            except Exception as e:
                logger.error(f"Error encoding texts: {e}")
                # Return zero embeddings as fallback
                new_embeddings = np.zeros((len(texts_to_encode), self.embedding_dim))

        # Combine cached and new embeddings
        if self.use_cache and cached_embeddings:
            all_embeddings = np.zeros((len(texts), self.embedding_dim))

            # Fill in cached embeddings
            cache_idx = 0
            new_idx = 0
            for i in range(len(texts)):
                if i in cache_indices:
                    all_embeddings[i] = new_embeddings[new_idx]
                    new_idx += 1
                else:
                    all_embeddings[i] = cached_embeddings[cache_idx]
                    cache_idx += 1

            embeddings = all_embeddings
        else:
            embeddings = new_embeddings

        return embeddings[0] if single_text else embeddings

    def encode_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Encode texts in batches

        Args:
            texts: List of texts to encode
            batch_size: Custom batch size

        Returns:
            List of embeddings
        """
        batch_size = batch_size or self.batch_size
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.encode(batch)
            embeddings.extend(batch_embeddings)

        return embeddings

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Use first 100 chars as key to avoid memory issues
        return text[:100] if len(text) > 100 else text

    def clear_cache(self):
        """Clear the embedding cache"""
        if self.use_cache:
            self._cache.clear()
            logger.info("Embedding cache cleared")

    def get_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between two embeddings

        Args:
            embedding1: First embedding
            embedding2: Second embedding
            metric: Similarity metric (cosine, euclidean, dot)

        Returns:
            Similarity score
        """
        if metric == "cosine":
            # Cosine similarity
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        elif metric == "euclidean":
            # Euclidean distance (inverted for similarity)
            distance = np.linalg.norm(embedding1 - embedding2)
            return float(1 / (1 + distance))

        elif metric == "dot":
            # Dot product
            return float(np.dot(embedding1, embedding2))

        else:
            raise ValueError(f"Unknown metric: {metric}")

    def batch_similarity(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray,
        metric: str = "cosine"
    ) -> np.ndarray:
        """
        Calculate similarity between query and multiple embeddings

        Args:
            query_embedding: Query embedding
            embeddings: Array of embeddings
            metric: Similarity metric

        Returns:
            Array of similarity scores
        """
        if metric == "cosine":
            # Normalize embeddings
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            # Calculate cosine similarity
            similarities = np.dot(embeddings_norm, query_norm)

        elif metric == "euclidean":
            # Calculate euclidean distance
            distances = np.linalg.norm(embeddings - query_embedding, axis=1)
            similarities = 1 / (1 + distances)

        elif metric == "dot":
            # Dot product
            similarities = np.dot(embeddings, query_embedding)

        else:
            raise ValueError(f"Unknown metric: {metric}")

        return similarities

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_sequence_length": self.max_length,
            "device": self.device,
            "batch_size": self.batch_size,
            "cache_enabled": self.use_cache,
            "cache_size": len(self._cache) if self.use_cache else 0,
        }

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text before encoding

        Args:
            text: Text to preprocess

        Returns:
            Preprocessed text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Truncate if too long
        if len(text) > self.max_length * 4:  # Rough char to token ratio
            text = text[:self.max_length * 4]

        return text

    def encode_with_metadata(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Encode text and return with metadata

        Args:
            text: Text to encode
            metadata: Optional metadata to include

        Returns:
            Dictionary with embedding and metadata
        """
        embedding = self.encode(text)

        result = {
            "text": text,
            "embedding": embedding.tolist() if isinstance(embedding, np.ndarray) else embedding,
            "embedding_model": self.model_name,
            "embedding_dim": self.embedding_dim,
        }

        if metadata:
            result["metadata"] = metadata

        return result

    async def generate_embeddings_async(
        self,
        texts: List[str]
    ) -> List[np.ndarray]:
        """
        Async wrapper for batch embedding generation

        Args:
            texts: List of texts to encode

        Returns:
            List of embeddings as numpy arrays
        """
        import asyncio

        # Run the sync method in a thread pool
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.encode_batch,
            texts
        )

        return embeddings


# Global singleton instance
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get singleton instance of EmbeddingService
    This ensures the model is loaded only once across the entire application
    """
    global _embedding_service_instance

    if _embedding_service_instance is None:
        logger.info("🧠 Initializing global EmbeddingService singleton")
        _embedding_service_instance = EmbeddingService()

    return _embedding_service_instance