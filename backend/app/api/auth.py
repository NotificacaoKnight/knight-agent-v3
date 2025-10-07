"""
Authentication endpoints
Microsoft Azure AD OAuth2 flow implementation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.api.deps import DatabaseSession, CurrentUser, OptionalUser
from app.core.rate_limiter import rate_limit_auth
from app.schemas.auth import (
    LoginUrlResponse,
    CallbackRequest,
    RefreshTokenRequest,
    MicrosoftTokenRequest,
    MicrosoftIdTokenRequest,
    TokenResponse,
    LoginResponse,
    LogoutResponse,
    UserInfo
)
from app.services.auth_service import auth_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create rate limiter for authentication endpoints
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"]
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
)

@router.get("/config")
async def get_public_config():
    """
    Get public authentication configuration for frontend

    Returns only public configuration that's safe to expose to frontend.
    Sensitive information like client secrets are never exposed.
    """
    return {
        "azure_ad": {
            "client_id": settings.AZURE_AD_CLIENT_ID,
            "tenant_id": settings.AZURE_AD_TENANT_ID,
            "redirect_uri": settings.AZURE_AD_REDIRECT_URI,
            "authority": f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}"
        },
        "features": {
            "csrf_enabled": settings.CSRF_ENABLED,
            "httponly_cookies": settings.USE_HTTPONLY_COOKIES,
            "secure_headers": settings.SECURE_HEADERS_ENABLED
        }
    }

def set_jwt_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """
    Set JWT tokens as httpOnly cookies

    Args:
        response: FastAPI response object
        access_token: JWT access token
        refresh_token: JWT refresh token
    """
    if settings.USE_HTTPONLY_COOKIES:
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,  # Always use COOKIE_SECURE setting
            samesite=settings.COOKIE_SAMESITE,
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )

        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,  # Always use COOKIE_SECURE setting
            samesite=settings.COOKIE_SAMESITE,
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/api/auth"  # Only send refresh token to auth endpoints
        )

def clear_jwt_cookies(response: Response) -> None:
    """
    Clear JWT cookies

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(
        key="access_token",
        domain=settings.COOKIE_DOMAIN,
        path="/"
    )
    response.delete_cookie(
        key="refresh_token",
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth"
    )

@router.get("/login", response_model=LoginUrlResponse)
async def login():
    """
    Get Microsoft OAuth2 login URL

    Returns the authorization URL to redirect the user to Microsoft login page.
    """
    try:
        auth_url = auth_service.get_auth_url()
        return LoginUrlResponse(auth_url=auth_url)
    except Exception as e:
        logger.error(f"Error generating login URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate login URL"
        )

@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str = None,
    db: DatabaseSession = None
):
    """
    Microsoft OAuth2 callback endpoint

    Handles the authorization code from Microsoft and exchanges it for tokens.
    This endpoint is called by Microsoft after successful authentication.

    Args:
        code: Authorization code from Microsoft
        state: State parameter for CSRF protection
        db: Database session

    Returns:
        Redirect to frontend with tokens or error
    """
    try:
        # Process the authorization callback
        result = await auth_service.process_auth_callback(code, db)

        # In production, redirect to frontend with tokens
        # For now, return the tokens directly
        return LoginResponse(**result)

    except ValueError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/callback", response_model=LoginResponse)
async def process_callback(
    request: CallbackRequest,
    db: DatabaseSession = None
):
    """
    Process OAuth2 callback (for frontend POST)

    Alternative endpoint for frontend to POST the authorization code.

    Args:
        request: Callback parameters with authorization code
        db: Database session

    Returns:
        Login response with tokens and user info
    """
    try:
        result = await auth_service.process_auth_callback(request.code, db)
        return LoginResponse(**result)
    except ValueError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 refresh attempts per minute
async def refresh_token(
    request: Request,
    response: Response,
    refresh_request: RefreshTokenRequest,
    db: DatabaseSession = None
):
    """
    Refresh access token using refresh token with rotation and device fingerprinting

    This endpoint implements:
    - Refresh token rotation (old token invalidated, new one issued)
    - Device fingerprinting validation
    - Rate limiting (10/minute per IP)
    - Automatic reuse detection (invalidates entire token family if reuse detected)

    Args:
        request: FastAPI request object (for device fingerprint)
        response: FastAPI response object (for setting cookies)
        refresh_request: Refresh token request
        db: Database session

    Returns:
        New access and refresh tokens
    """
    try:
        # Get device fingerprint data
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else ""

        # Call refresh service with device fingerprinting
        result = await auth_service.refresh_token_with_rotation(
            refresh_token=refresh_request.refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            db=db
        )

        # Set new tokens in httpOnly cookies
        set_jwt_cookies(response, result["access_token"], result["refresh_token"])

        return TokenResponse(**result)

    except ValueError as e:
        # Invalid token, expired, or reuse detected
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: CurrentUser
):
    """
    Get current authenticated user information

    Args:
        current_user: Current authenticated user from token

    Returns:
        User information
    """
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        preferred_name=current_user.preferred_name,
        profile_picture=current_user.profile_picture,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        preferred_language=current_user.preferred_language,
        department=current_user.department,
        job_title=current_user.job_title,
        created_at=current_user.created_at
    )

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DatabaseSession = None
):
    """
    Logout current user

    Note: With JWT tokens, logout is primarily handled on the frontend
    by removing the token from storage. This endpoint also blacklists
    the current token and deactivates sessions for additional security.

    Args:
        request: FastAPI request object (to get current token)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Logout confirmation
    """
    try:
        # Get the current token from authorization header and blacklist it
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            from app.core.security import blacklist_token
            await blacklist_token(token)

        # Deactivate user sessions for additional security
        success = await auth_service.logout_user(current_user.id, db)

        # Clear JWT cookies
        clear_jwt_cookies(response)

        return LogoutResponse(
            message="Successfully logged out",
            success=True
        )

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )

@router.get("/verify")
async def verify_token(
    current_user: OptionalUser
):
    """
    Verify if the current token is valid

    Returns:
        Token validation status
    """
    return {
        "valid": current_user is not None,
        "user_id": current_user.id if current_user else None
    }

@router.post("/microsoft/token", response_model=LoginResponse)
async def microsoft_token_login(
    response: Response,
    microsoft_request: MicrosoftTokenRequest,
    db: DatabaseSession = None
):
    """
    Microsoft token exchange endpoint

    Receives Microsoft access token from frontend (MSAL) and creates/updates user session.
    This is the main endpoint used by the frontend after MSAL login.

    Args:
        request: Microsoft token exchange request with access_token
        db: Database session

    Returns:
        Login response with session token and user info
    """
    try:
        logger.info("=== MICROSOFT TOKEN ENDPOINT DEBUG ===")
        logger.info(f"Token length: {len(microsoft_request.access_token)}")
        logger.info(f"Token segments: {microsoft_request.access_token.count('.') + 1}")
        logger.info(f"Token preview: {microsoft_request.access_token[:50]}...")

        # Use the existing auth service to process the Microsoft token
        # This will validate the token, create/update user, and generate session
        result = await auth_service.process_microsoft_token(microsoft_request.access_token, db)

        # Set JWT cookies if enabled
        set_jwt_cookies(response, result["access_token"], result["refresh_token"])

        return LoginResponse(**result)
    except ValueError as e:
        logger.error(f"Microsoft token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in Microsoft token exchange: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/microsoft/id-token", response_model=LoginResponse)
async def microsoft_id_token_login(
    response: Response,
    microsoft_request: MicrosoftIdTokenRequest,
    db: DatabaseSession = None
):
    """
    Microsoft ID Token + Access Token exchange endpoint (RECOMMENDED)

    Receives Microsoft ID token (for authentication) and access token (for Graph API)
    from frontend (MSAL) and creates/updates user session.

    This is the SECURE method that validates ID tokens properly.

    Args:
        microsoft_request: Microsoft request with both id_token and access_token
        db: Database session

    Returns:
        Login response with session token and user info
    """
    try:
        logger.info("🔐 MICROSOFT ID TOKEN ENDPOINT (SECURE) ===")
        logger.info(f"ID Token length: {len(microsoft_request.id_token)}")
        logger.info(f"Access Token length: {len(microsoft_request.access_token)}")
        logger.info(f"ID Token segments: {microsoft_request.id_token.count('.') + 1}")
        logger.info(f"Access Token segments: {microsoft_request.access_token.count('.') + 1}")

        # Use the new ID token validation method
        result = await auth_service.process_microsoft_id_token(
            microsoft_request.id_token,
            microsoft_request.access_token,
            db
        )

        # Set JWT cookies if enabled
        set_jwt_cookies(response, result["access_token"], result["refresh_token"])

        return LoginResponse(**result)
    except ValueError as e:
        logger.error(f"Microsoft ID token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in Microsoft ID token exchange: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.put("/profile", response_model=UserInfo)
async def update_user_profile(
    profile_data: dict,
    current_user: CurrentUser,
    db: DatabaseSession = None
):
    """
    Update user profile information

    Allows users to update their profile information like display name,
    department, and job title.

    Args:
        profile_data: Dictionary with profile fields to update
        current_user: Current authenticated user from token
        db: Database session

    Returns:
        Updated user profile information
    """
    try:
        # Update user profile via auth service
        updated_user = await auth_service.update_user_profile(
            current_user.id, profile_data, db
        )

        return UserInfo(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            display_name=updated_user.display_name,
            is_admin=updated_user.is_admin,
            is_active=updated_user.is_active,
            preferred_language=updated_user.preferred_language,
            department=updated_user.department,
            job_title=updated_user.job_title,
            created_at=updated_user.created_at
        )
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.post("/debug-token", include_in_schema=False)
async def debug_microsoft_token(
    request: MicrosoftTokenRequest,
    db: DatabaseSession = None
):
    """
    DEBUG ENDPOINT: Decode and display token claims without validation
    This endpoint should be removed in production
    """
    import jwt

    try:
        # Decode without verification to see what's in the token
        decoded = jwt.decode(
            request.access_token,
            options={"verify_signature": False}
        )

        # Get header
        header = jwt.get_unverified_header(request.access_token)

        # Token segments
        segments = request.access_token.count('.') + 1

        return {
            "status": "debug_info",
            "token_length": len(request.access_token),
            "segments": segments,
            "header": header,
            "claims": decoded,
            "important_fields": {
                "aud": decoded.get("aud", "NOT_FOUND"),
                "iss": decoded.get("iss", "NOT_FOUND"),
                "sub": decoded.get("sub", "NOT_FOUND"),
                "exp": decoded.get("exp", "NOT_FOUND"),
                "iat": decoded.get("iat", "NOT_FOUND"),
                "preferred_username": decoded.get("preferred_username", "NOT_FOUND"),
                "name": decoded.get("name", "NOT_FOUND"),
                "tid": decoded.get("tid", "NOT_FOUND"),
                "oid": decoded.get("oid", "NOT_FOUND")
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "token_preview": request.access_token[:50] + "..."
        }


@router.post("/preferences")
async def update_language_preference(
    preferences: dict,
    current_user: CurrentUser,
    db: DatabaseSession = None
):
    """
    Update user language preference

    Updates the user's preferred language setting.

    Args:
        preferences: Dictionary with language preference
        current_user: Current authenticated user from token
        db: Database session

    Returns:
        Success confirmation
    """
    try:
        language = preferences.get("language", "pt")
        success = await auth_service.update_language_preference(
            current_user.id, language, db
        )

        if success:
            return {"message": "Language preference updated successfully", "language": language}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update language preference"
            )
    except Exception as e:
        logger.error(f"Language preference update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update language preference"
        )