"""
Multi-layer Cache Service
Implements L1 (in-memory), L2 (Redis), and L3 (Database) caching
"""
import json
import hashlib
import pickle
import logging
from functools import lru_cache, wraps
from typing import Any, Optional, Dict, Callable, Union
from datetime import datetime, timedelta
import asyncio

from app.core.redis_service import redis_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """
    Multi-layer cache implementation
    L1: In-memory LRU cache (fastest, limited size)
    L2: Redis cache (fast, distributed)
    L3: Database cache (slower, persistent)
    """

    def __init__(self):
        self.redis = redis_service
        self.stats = {
            'l1_hits': 0,
            'l1_misses': 0,
            'l2_hits': 0,
            'l2_misses': 0,
            'l3_hits': 0,
            'l3_misses': 0,
            'total_requests': 0
        }

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a unique cache key based on function arguments

        Args:
            prefix: Cache key prefix
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Unique cache key string
        """
        # Create a string representation of all arguments
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # For complex objects, use a hash
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}:{v}")
            else:
                key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")

        return ":".join(key_parts)

    async def get_from_cache(
        self,
        key: str,
        level: int = 2
    ) -> Optional[Any]:
        """
        Get value from cache (checking L1, then L2)

        Args:
            key: Cache key
            level: Maximum cache level to check (1=L1 only, 2=L1+L2)

        Returns:
            Cached value or None
        """
        self.stats['total_requests'] += 1

        # L1 cache is handled by lru_cache decorator
        # This method handles L2 (Redis) cache

        if level >= 2:
            try:
                # Try L2 cache (Redis)
                cached_value = await self.redis.get(key)
                if cached_value:
                    self.stats['l2_hits'] += 1
                    logger.debug(f"L2 cache hit for key: {key}")

                    # Deserialize the cached value
                    try:
                        return json.loads(cached_value)
                    except json.JSONDecodeError:
                        # Try pickle for complex objects
                        return pickle.loads(cached_value.encode('latin1'))
                else:
                    self.stats['l2_misses'] += 1
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
                self.stats['l2_misses'] += 1

        return None

    async def set_in_cache(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        level: int = 2
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            level: Cache levels to set (1=L1 only, 2=L1+L2)

        Returns:
            Success status
        """
        if level >= 2:
            try:
                # Serialize the value
                try:
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    # Use pickle for complex objects
                    serialized = pickle.dumps(value).decode('latin1')

                # Set in L2 cache (Redis)
                await self.redis.set(key, serialized, ttl=ttl)
                logger.debug(f"Cached in L2: {key} (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"Failed to cache in Redis: {e}")
                return False

        return True

    async def invalidate_cache(
        self,
        pattern: str = None,
        key: str = None
    ) -> int:
        """
        Invalidate cache entries

        Args:
            pattern: Pattern to match keys (e.g., "user:*")
            key: Specific key to invalidate

        Returns:
            Number of keys invalidated
        """
        count = 0

        if key:
            # Invalidate specific key
            deleted = await self.redis.delete(key)
            count += deleted
        elif pattern:
            # Invalidate by pattern
            keys = await self.redis.keys(pattern)
            if keys:
                for key in keys:
                    deleted = await self.redis.delete(key)
                    count += deleted

        logger.info(f"Invalidated {count} cache entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary of cache statistics
        """
        total = self.stats['total_requests']
        if total > 0:
            l1_hit_rate = (self.stats['l1_hits'] / total) * 100
            l2_hit_rate = (self.stats['l2_hits'] / total) * 100
            overall_hit_rate = ((self.stats['l1_hits'] + self.stats['l2_hits']) / total) * 100
        else:
            l1_hit_rate = l2_hit_rate = overall_hit_rate = 0

        return {
            **self.stats,
            'l1_hit_rate': f"{l1_hit_rate:.2f}%",
            'l2_hit_rate': f"{l2_hit_rate:.2f}%",
            'overall_hit_rate': f"{overall_hit_rate:.2f}%"
        }

# Global cache instance
cache_service = CacheService()

# Decorator for L1 cache (in-memory)
def cache_l1(maxsize: int = 128, ttl_seconds: int = 300):
    """
    L1 cache decorator using LRU cache with TTL

    Args:
        maxsize: Maximum number of cached items
        ttl_seconds: Time to live in seconds

    Returns:
        Decorated function with L1 caching
    """
    def decorator(func):
        # Create a cached version with TTL
        cache_data = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = str((args, tuple(sorted(kwargs.items()))))

            # Check if cached and not expired
            if key in cache_data:
                value, timestamp = cache_data[key]
                if datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
                    cache_service.stats['l1_hits'] += 1
                    logger.debug(f"L1 cache hit for {func.__name__}")
                    return value

            # Cache miss or expired
            cache_service.stats['l1_misses'] += 1
            value = func(*args, **kwargs)

            # Store in cache with timestamp
            cache_data[key] = (value, datetime.now())

            # Limit cache size
            if len(cache_data) > maxsize:
                oldest_key = min(cache_data.keys(), key=lambda k: cache_data[k][1])
                del cache_data[oldest_key]

            return value

        wrapper.cache_clear = lambda: cache_data.clear()
        return wrapper
    return decorator

# Decorator for L2 cache (Redis)
def cache_l2(prefix: str, ttl: int = 3600):
    """
    L2 cache decorator using Redis

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds

    Returns:
        Decorated async function with L2 caching
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_service.generate_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached = await cache_service.get_from_cache(cache_key)
            if cached is not None:
                return cached

            # Cache miss - execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_service.set_in_cache(cache_key, result, ttl=ttl)

            return result

        wrapper.cache_key = lambda *args, **kwargs: cache_service.generate_cache_key(
            prefix, *args, **kwargs
        )
        return wrapper
    return decorator

# Combined L1+L2 cache decorator
def cache_multi(
    prefix: str,
    l1_maxsize: int = 128,
    l1_ttl: int = 300,
    l2_ttl: int = 3600
):
    """
    Multi-layer cache decorator (L1 + L2)

    Args:
        prefix: Cache key prefix
        l1_maxsize: L1 cache max size
        l1_ttl: L1 TTL in seconds
        l2_ttl: L2 TTL in seconds

    Returns:
        Decorated function with multi-layer caching
    """
    def decorator(func):
        # Apply L1 cache
        cached_func = cache_l1(maxsize=l1_maxsize, ttl_seconds=l1_ttl)(func)

        # Apply L2 cache
        @wraps(cached_func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_service.generate_cache_key(prefix, *args, **kwargs)

            # Try L2 cache if L1 misses
            try:
                result = cached_func(*args, **kwargs)
                return result
            except:
                # L1 miss, try L2
                cached = await cache_service.get_from_cache(cache_key)
                if cached is not None:
                    return cached

                # Both L1 and L2 miss - execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Store in L2 cache
                await cache_service.set_in_cache(cache_key, result, ttl=l2_ttl)

                return result

        return wrapper
    return decorator

# Specialized cache for embeddings
class EmbeddingCache:
    """
    Specialized cache for embeddings with compression
    """

    def __init__(self):
        self.cache = cache_service

    async def get_embedding(self, text: str) -> Optional[Any]:
        """
        Get cached embedding for text

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding or None
        """
        # Generate unique key for text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"embedding:{text_hash}"

        return await self.cache.get_from_cache(cache_key)

    async def set_embedding(self, text: str, embedding: Any, ttl: int = 604800):
        """
        Cache embedding for text

        Args:
            text: Original text
            embedding: Embedding vector
            ttl: Time to live (default 7 days)

        Returns:
            Success status
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cache_key = f"embedding:{text_hash}"

        # Optionally compress embedding here if needed
        return await self.cache.set_in_cache(cache_key, embedding, ttl=ttl)

    async def get_or_compute(
        self,
        text: str,
        compute_func: Callable,
        ttl: int = 604800
    ) -> Any:
        """
        Get embedding from cache or compute if missing

        Args:
            text: Text to get embedding for
            compute_func: Function to compute embedding
            ttl: Time to live for cache

        Returns:
            Embedding vector
        """
        # Try cache first
        cached = await self.get_embedding(text)
        if cached is not None:
            logger.debug(f"Embedding cache hit for text hash")
            return cached

        # Compute embedding
        logger.debug(f"Computing new embedding for text")
        if asyncio.iscoroutinefunction(compute_func):
            embedding = await compute_func(text)
        else:
            embedding = compute_func(text)

        # Cache the result
        await self.set_embedding(text, embedding, ttl=ttl)

        return embedding

# Global embedding cache instance
embedding_cache = EmbeddingCache()