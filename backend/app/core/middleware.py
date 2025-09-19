"""
Custom middleware for FastAPI
Includes authentication, rate limiting, and security
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time
import logging
import uuid
from typing import Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.models.user import UserSession
from app.core.security import generate_csrf_token, verify_csrf_token
from app.core.rate_limiter import RateLimitMiddleware as RedisRateLimitMiddleware
from app.core.log_sanitizer import sanitize_headers, sanitize_request_body

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracking
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add request ID to request and response"""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add to logs
        logger.info(f"Request {request_id}: {request.method} {request.url.path}")

        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        logger.info(
            f"Request {request_id} completed in {process_time:.2f}s "
            f"with status {response.status_code}"
        )

        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers"""
        response = await call_next(request)

        if not settings.SECURE_HEADERS_ENABLED:
            return response

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        csp_header = f"default-src {settings.CSP_DEFAULT_SRC}; " \
                    f"script-src {settings.CSP_SCRIPT_SRC}; " \
                    f"style-src {settings.CSP_STYLE_SRC}; " \
                    f"img-src {settings.CSP_IMG_SRC}; " \
                    f"connect-src {settings.CSP_CONNECT_SRC}; " \
                    "object-src 'none'; " \
                    "base-uri 'self'; " \
                    "form-action 'self'"

        response.headers["Content-Security-Policy"] = csp_header

        # HSTS header (only for HTTPS)
        if request.url.scheme == "https" or not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # COOP/COEP headers temporarily disabled for MSAL popup compatibility
        # Uncomment when not using popup-based authentication
        # response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        # response.headers["Cross-Origin-Embedder-Policy"] = "unsafe-none"

        # Note: Cannot remove server header in middleware (read-only)

        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests and responses with sensitive data sanitization
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log request details with sanitization"""
        # Get request body if needed
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Sanitize headers for logging
        safe_headers = sanitize_headers(dict(request.headers))

        # Sanitize body for logging
        safe_body = "No body"
        if body:
            safe_body = sanitize_request_body(body)
            # Truncate if too long
            if len(safe_body) > 500:
                safe_body = safe_body[:500] + "... [TRUNCATED]"

        logger.debug(
            f"Request: {request.method} {request.url.path} "
            f"Headers: {safe_headers} "
            f"Body: {safe_body}"
        )

        # Process request
        response = await call_next(request)

        # Log response (without sensitive data)
        logger.debug(f"Response: Status {response.status_code}")

        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle errors globally"""
        try:
            response = await call_next(request)
            return response
        except HTTPException as exc:
            # HTTP exceptions are already handled properly
            raise exc
        except Exception as exc:
            # Log unexpected errors
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"Unhandled error in request {request_id}: {exc}",
                exc_info=True
            )

            # Return generic error
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred",
                    "request_id": request_id
                }
            )

class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware
    """

    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths exempt from CSRF protection
    EXEMPT_PATHS = {
        "/api/auth/microsoft/token",  # Microsoft token exchange
        "/api/auth/callback",         # OAuth callback
        "/api/auth/microsoft/callback", # OAuth callback
        "/docs",                      # Swagger docs
        "/openapi.json",             # OpenAPI spec
    }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add CSRF protection"""

        # Skip CSRF for safe methods
        if request.method not in self.PROTECTED_METHODS:
            response = await call_next(request)
            # Add CSRF token to safe responses for later use
            if request.method == "GET":
                csrf_token = generate_csrf_token()
                response.headers["X-CSRF-Token"] = csrf_token
                response.set_cookie(
                    key="csrf_token",
                    value=csrf_token,
                    httponly=False,  # Frontend needs to read this
                    secure=not settings.DEBUG,
                    samesite="strict"
                )
            return response

        # Skip CSRF for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip CSRF if explicitly disabled (but NOT for debug mode)
        if not settings.CSRF_ENABLED:
            logger.debug("CSRF protection disabled by configuration")
            return await call_next(request)

        # Get CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            # Try to get from form data for form submissions
            if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
                try:
                    form_data = await request.form()
                    csrf_token = form_data.get("csrf_token")
                except:
                    pass

        # Get expected token from cookie
        expected_token = request.cookies.get("csrf_token")

        # Verify CSRF token
        if not csrf_token or not expected_token or not verify_csrf_token(csrf_token, expected_token):
            logger.warning(f"CSRF token validation failed for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token validation failed"}
            )

        # Process request
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware using simple in-memory storage
    In production, use Redis for distributed rate limiting
    """

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._requests = {}  # {client_ip: [(timestamp, count), ...]}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply rate limiting based on client IP"""

        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client IP
        client_ip = request.headers.get("X-Real-IP") or \
                   request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                   request.client.host if request.client else "unknown"

        # Clean old entries for this IP
        now = time.time()
        if client_ip in self._requests:
            self._requests[client_ip] = [
                (ts, count) for ts, count in self._requests[client_ip]
                if now - ts < self.period
            ]

        # Count requests in current period
        current_requests = sum(
            count for ts, count in self._requests.get(client_ip, [])
        )

        # Check if rate limit exceeded
        if current_requests >= self.calls:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.period
                },
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + self.period)),
                    "Retry-After": str(self.period)
                }
            )

        # Process request
        response = await call_next(request)

        # Record this request
        if client_ip not in self._requests:
            self._requests[client_ip] = []
        self._requests[client_ip].append((now, 1))

        # Add rate limit headers
        remaining = max(0, self.calls - current_requests - 1)
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))

        return response

def setup_middlewares(app):
    """
    Setup all custom middlewares
    Called from main.py
    """
    # Order matters - they execute in reverse order
    app.add_middleware(ErrorHandlingMiddleware)
    # CSRF and Security headers removed - not needed for JWT API

    # Use Redis-based rate limiting (with in-memory fallback)
    app.add_middleware(
        RedisRateLimitMiddleware,
        calls=settings.RATE_LIMIT_REQUESTS,
        period=settings.RATE_LIMIT_PERIOD,
        enabled=settings.RATE_LIMIT_ENABLED
    )

    if settings.DEBUG:
        app.add_middleware(LoggingMiddleware)

    app.add_middleware(RequestIDMiddleware)
    # Note: Authentication is now handled by FastAPI dependencies, not middleware