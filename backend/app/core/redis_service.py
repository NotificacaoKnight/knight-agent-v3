"""
Redis service for token blacklist and caching
"""
import logging
from typing import Optional, Set
import redis.asyncio as redis
from datetime import datetime, timedelta
import json

from app.core.config import settings
from app.core.security import decode_token

logger = logging.getLogger(__name__)

class RedisService:
    """
    Service for managing Redis connections and token blacklist
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._fallback_blacklist: Set[str] = set()  # In-memory fallback

    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Redis: {e}")
            logger.warning("🔄 Using in-memory fallback for token blacklist")
            self.redis_client = None

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.ping()
            return True
        except:
            return False

    async def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist

        Args:
            token: JWT token to blacklist

        Returns:
            True if successfully blacklisted
        """
        try:
            # Decode token to get expiration
            payload = decode_token(token)
            if not payload:
                logger.warning("Cannot blacklist invalid token")
                return False

            exp = payload.get("exp")
            if not exp:
                logger.warning("Token has no expiration, cannot determine TTL")
                return False

            # Calculate TTL (time until token expires)
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            ttl = int((exp_datetime - now).total_seconds())

            if ttl <= 0:
                logger.debug("Token already expired, no need to blacklist")
                return True

            # Try Redis first
            if await self.is_connected():
                key = f"blacklist:{token}"
                await self.redis_client.setex(key, ttl, "1")
                logger.debug(f"Token blacklisted in Redis with TTL {ttl}s")
                return True
            else:
                # Fallback to in-memory
                self._fallback_blacklist.add(token)
                logger.debug("Token blacklisted in memory (fallback)")
                return True

        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
            # Emergency fallback
            self._fallback_blacklist.add(token)
            return True

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted
        """
        try:
            # Check Redis first
            if await self.is_connected():
                key = f"blacklist:{token}"
                result = await self.redis_client.exists(key)
                if result:
                    logger.debug("Token found in Redis blacklist")
                    return True

            # Check in-memory fallback
            if token in self._fallback_blacklist:
                logger.debug("Token found in memory blacklist")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            # If Redis fails, check memory fallback
            return token in self._fallback_blacklist

    async def cleanup_expired_blacklist(self) -> int:
        """
        Clean up expired tokens from in-memory fallback
        Redis TTL handles this automatically

        Returns:
            Number of tokens cleaned up
        """
        if not self._fallback_blacklist:
            return 0

        cleaned = 0
        expired_tokens = set()

        for token in self._fallback_blacklist:
            try:
                payload = decode_token(token)
                if not payload:
                    # Invalid token, remove it
                    expired_tokens.add(token)
                    continue

                exp = payload.get("exp")
                if exp:
                    exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                    if datetime.now(timezone.utc) > exp_datetime:
                        expired_tokens.add(token)
            except Exception:
                # If we can't decode, consider it expired
                expired_tokens.add(token)

        self._fallback_blacklist -= expired_tokens
        cleaned = len(expired_tokens)

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired tokens from memory")

        return cleaned

    async def get_stats(self) -> dict:
        """
        Get blacklist statistics

        Returns:
            Dictionary with statistics
        """
        redis_connected = await self.is_connected()
        memory_count = len(self._fallback_blacklist)

        stats = {
            "redis_connected": redis_connected,
            "memory_blacklist_count": memory_count,
        }

        if redis_connected:
            try:
                # Count blacklisted tokens in Redis
                keys = await self.redis_client.keys("blacklist:*")
                stats["redis_blacklist_count"] = len(keys)
            except Exception:
                stats["redis_blacklist_count"] = "error"

        return stats

# Global Redis service instance
redis_service = RedisService()

async def get_redis_service() -> RedisService:
    """Get Redis service instance"""
    return redis_service