"""
Security utilities for authentication and authorization
JWT handling, password hashing, and token validation
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.JWT_SECRET_KEY or settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password
    """
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    # Validate JWT format (must have exactly 3 parts separated by dots)
    if not token or not isinstance(token, str) or token.count('.') != 2:
        logger.debug(f"Invalid JWT format: token does not have 3 segments")
        return None

    # Check if token is not just dots
    parts = token.split('.')
    if any(not part for part in parts):
        logger.debug(f"Invalid JWT format: empty segments found")
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None

async def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify a token and check its type (async)

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload or None if invalid
    """
    # Check if token is blacklisted (async)
    if await is_token_blacklisted(token):
        logger.warning("Token is blacklisted")
        return None

    payload = decode_token(token)

    if not payload:
        return None

    # Check token type
    if payload.get("type") != token_type:
        logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
        return None

    # Check expiration (jose already checks this, but being explicit)
    exp = payload.get("exp")
    if exp:
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) > exp_datetime:
            logger.warning("Token has expired")
            return None

    return payload

def verify_token_sync(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Synchronous version for backward compatibility
    """
    # Check if token is blacklisted (sync)
    if is_token_blacklisted_sync(token):
        logger.warning("Token is blacklisted")
        return None

    payload = decode_token(token)

    if not payload:
        return None

    # Check token type
    if payload.get("type") != token_type:
        logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
        return None

    # Check expiration
    exp = payload.get("exp")
    if exp:
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) > exp_datetime:
            logger.warning("Token has expired")
            return None

    return payload

def generate_session_token() -> str:
    """
    Generate a secure random session token

    Returns:
        A secure random token string
    """
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    """
    Generate a secure API key

    Returns:
        A secure API key string
    """
    return f"sk_{secrets.token_urlsafe(32)}"

def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token

    Returns:
        A secure CSRF token string
    """
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, expected_token: str) -> bool:
    """
    Verify CSRF token using constant-time comparison

    Args:
        token: The CSRF token to verify
        expected_token: The expected CSRF token

    Returns:
        True if tokens match
    """
    if not token or not expected_token:
        return False
    return secrets.compare_digest(token, expected_token)

# Token blacklist functions (async wrappers for Redis service)
async def blacklist_token(token: str) -> bool:
    """
    Add token to blacklist (async)

    Args:
        token: JWT token to blacklist

    Returns:
        True if successfully blacklisted
    """
    from app.core.redis_service import redis_service
    return await redis_service.blacklist_token(token)

async def is_token_blacklisted(token: str) -> bool:
    """
    Check if token is blacklisted (async)

    Args:
        token: JWT token to check

    Returns:
        True if token is blacklisted
    """
    from app.core.redis_service import redis_service
    return await redis_service.is_token_blacklisted(token)

# Synchronous fallback for compatibility
_sync_blacklist = set()

def blacklist_token_sync(token: str) -> None:
    """Synchronous fallback for token blacklisting"""
    _sync_blacklist.add(token)

def is_token_blacklisted_sync(token: str) -> bool:
    """Synchronous fallback for token checking"""
    return token in _sync_blacklist

class SecurityContext:
    """
    Security context for request-scoped authentication data
    """

    def __init__(self):
        self.user_id: Optional[int] = None
        self.session_id: Optional[int] = None
        self.is_admin: bool = False
        self.permissions: list[str] = []

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.user_id is not None

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or self.is_admin

    def require_admin(self):
        """Require admin access or raise exception"""
        if not self.is_admin:
            raise PermissionError("Admin access required")

    def require_authenticated(self):
        """Require authentication or raise exception"""
        if not self.is_authenticated:
            raise PermissionError("Authentication required")