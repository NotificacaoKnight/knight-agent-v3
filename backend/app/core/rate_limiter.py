"""
Redis-based Rate Limiter for FastAPI
Provides distributed rate limiting using Redis
"""
import time
import logging
from typing import Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings
from app.core.redis_service import redis_service

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm
    """

    def __init__(self, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter

        Args:
            calls: Number of allowed calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self._fallback_storage = {}  # In-memory fallback

    async def check_rate_limit(
        self,
        key: str,
        calls: Optional[int] = None,
        period: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """
        Check if rate limit is exceeded

        Args:
            key: Unique key for rate limiting (e.g., IP address or user ID)
            calls: Override default number of calls
            period: Override default period

        Returns:
            Tuple of (is_allowed, remaining_calls, reset_time)
        """
        calls = calls or self.calls
        period = period or self.period

        # Try Redis first
        if await redis_service.is_connected():
            return await self._check_redis_rate_limit(key, calls, period)
        else:
            # Fallback to in-memory
            logger.warning("Redis not available, using in-memory rate limiting")
            return self._check_memory_rate_limit(key, calls, period)

    async def _check_redis_rate_limit(
        self,
        key: str,
        calls: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window

        Args:
            key: Rate limit key
            calls: Number of allowed calls
            period: Time period in seconds

        Returns:
            Tuple of (is_allowed, remaining_calls, reset_time)
        """
        try:
            redis_key = f"rate_limit:{key}"
            now = time.time()
            window_start = now - period

            # Remove old entries outside the window
            await redis_service.redis_client.zremrangebyscore(
                redis_key, 0, window_start
            )

            # Count requests in current window
            current_requests = await redis_service.redis_client.zcard(redis_key)

            if current_requests >= calls:
                # Get the oldest request time to calculate reset
                oldest = await redis_service.redis_client.zrange(
                    redis_key, 0, 0, withscores=True
                )
                reset_time = int(oldest[0][1] + period) if oldest else int(now + period)
                return False, 0, reset_time

            # Add current request
            await redis_service.redis_client.zadd(redis_key, {str(now): now})

            # Set expiry on the key
            await redis_service.redis_client.expire(redis_key, period)

            remaining = max(0, calls - current_requests - 1)
            reset_time = int(now + period)

            return True, remaining, reset_time

        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall back to allowing the request on error
            return True, calls - 1, int(time.time() + period)

    def _check_memory_rate_limit(
        self,
        key: str,
        calls: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using in-memory storage (fallback)

        Args:
            key: Rate limit key
            calls: Number of allowed calls
            period: Time period in seconds

        Returns:
            Tuple of (is_allowed, remaining_calls, reset_time)
        """
        now = time.time()
        window_start = now - period

        # Clean old entries
        if key in self._fallback_storage:
            self._fallback_storage[key] = [
                timestamp for timestamp in self._fallback_storage[key]
                if timestamp > window_start
            ]

        # Count requests in window
        current_requests = len(self._fallback_storage.get(key, []))

        if current_requests >= calls:
            # Calculate reset time
            oldest = min(self._fallback_storage[key]) if self._fallback_storage[key] else now
            reset_time = int(oldest + period)
            return False, 0, reset_time

        # Add current request
        if key not in self._fallback_storage:
            self._fallback_storage[key] = []
        self._fallback_storage[key].append(now)

        remaining = max(0, calls - current_requests - 1)
        reset_time = int(now + period)

        return True, remaining, reset_time

    def get_client_key(self, request: Request) -> str:
        """
        Get unique client key for rate limiting

        Args:
            request: FastAPI request object

        Returns:
            Unique client identifier
        """
        # Try to get authenticated user ID first
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.id}"

        # Fall back to IP address
        client_ip = request.headers.get("X-Real-IP") or \
                   request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                   request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting middleware
    """

    def __init__(
        self,
        app,
        calls: int = 100,
        period: int = 60,
        enabled: bool = True
    ):
        super().__init__(app)
        self.rate_limiter = RedisRateLimiter(calls, period)
        self.enabled = enabled

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply rate limiting"""

        # Skip if disabled
        if not self.enabled or not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client key
        client_key = self.rate_limiter.get_client_key(request)

        # Check rate limit
        is_allowed, remaining, reset_time = await self.rate_limiter.check_rate_limit(
            client_key
        )

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_key}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": reset_time - int(time.time())
                },
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time()))
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


# Decorator for per-endpoint rate limiting
class RateLimitDecorator:
    """
    Decorator for applying rate limits to specific endpoints
    """

    def __init__(self, calls: int = 10, period: int = 60):
        """
        Initialize rate limit decorator

        Args:
            calls: Number of allowed calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.rate_limiter = RedisRateLimiter(calls, period)

    async def __call__(self, request: Request):
        """
        Check rate limit for decorated endpoint

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit exceeded
        """
        client_key = self.rate_limiter.get_client_key(request)

        is_allowed, remaining, reset_time = await self.rate_limiter.check_rate_limit(
            client_key,
            self.calls,
            self.period
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time()))
                }
            )

        # Add rate limit info to request state
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_reset = reset_time


# Convenience functions for common rate limits
def rate_limit_auth(calls: int = 5, period: int = 60):
    """Rate limit for authentication endpoints"""
    return RateLimitDecorator(calls, period)


def rate_limit_api(calls: int = 100, period: int = 60):
    """Rate limit for general API endpoints"""
    return RateLimitDecorator(calls, period)


def rate_limit_heavy(calls: int = 10, period: int = 60):
    """Rate limit for resource-intensive endpoints"""
    return RateLimitDecorator(calls, period)