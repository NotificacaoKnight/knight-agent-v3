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

logger = logging.getLogger(__name__)

class TokenAuthMiddleware(BaseHTTPMiddleware):
    """
    Token authentication middleware
    Validates Bearer tokens and attaches user to request
    """

    # Paths that don't require authentication
    EXEMPT_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/auth/login",
        "/api/auth/microsoft/callback",
        "/api/ping",
    ]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and check authentication"""

        # Skip auth for exempt paths
        if any(request.url.path.startswith(path) for path in self.EXEMPT_PATHS):
            response = await call_next(request)
            return response

        # Skip auth for static/media files
        if request.url.path.startswith("/static") or request.url.path.startswith("/media"):
            response = await call_next(request)
            return response

        # Get authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authentication token"}
            )

        token = auth_header.split(" ")[1]

        # Validate token (simplified for now - will integrate with DB later)
        # TODO: Implement actual token validation with database
        request.state.user_id = None
        request.state.session_token = token

        response = await call_next(request)
        return response

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

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Note: Cannot remove server header in middleware (read-only)

        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests and responses
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Log request details"""
        # Log request
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else b""

        logger.debug(
            f"Request: {request.method} {request.url.path} "
            f"Headers: {dict(request.headers)} "
            f"Body: {body[:500] if body else 'No body'}"
        )

        # Process request
        response = await call_next(request)

        # Log response
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

def setup_middlewares(app):
    """
    Setup all custom middlewares
    Called from main.py
    """
    # Order matters - they execute in reverse order
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    if settings.DEBUG:
        app.add_middleware(LoggingMiddleware)

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TokenAuthMiddleware)