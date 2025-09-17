"""
FastAPI dependencies for authentication and database
Common dependencies used across the application
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import verify_token
from app.models.user import User
from app.services.auth_service import auth_service

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"]
)

# Security scheme for Swagger UI
security = HTTPBearer(
    scheme_name="Bearer",
    description="JWT Bearer token",
    bearerFormat="JWT"
)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    # Verify token
    payload = verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Add user to request state for middleware access
    request.state.user = user
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user

    Args:
        current_user: Current authenticated user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current admin user

    Args:
        current_user: Current active user

    Returns:
        Current admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise

    Args:
        request: FastAPI request object
        credentials: Optional Bearer token
        db: Database session

    Returns:
        Current user or None
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = verify_token(token, token_type="access")

        if payload:
            user = await auth_service.get_current_user(token, db)
            if user:
                request.state.user = user
                return user
    except Exception:
        pass

    return None

# Type aliases for cleaner code
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_current_user)]
DatabaseSession = Annotated[AsyncSession, Depends(get_async_db)]