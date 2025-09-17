"""
Authentication endpoints
Microsoft Azure AD OAuth2 flow implementation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
import logging

from app.api.deps import DatabaseSession, CurrentUser, OptionalUser
from app.schemas.auth import (
    LoginUrlResponse,
    CallbackRequest,
    RefreshTokenRequest,
    MicrosoftTokenRequest,
    TokenResponse,
    LoginResponse,
    LogoutResponse,
    UserInfo
)
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"}
    }
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
async def refresh_token(
    request: RefreshTokenRequest,
    db: DatabaseSession = None
):
    """
    Refresh access token using refresh token

    Args:
        request: Refresh token request
        db: Database session

    Returns:
        New access and refresh tokens
    """
    try:
        result = await auth_service.refresh_token(request.refresh_token, db)
        return TokenResponse(**result)
    except ValueError as e:
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
    current_user: CurrentUser,
    db: DatabaseSession = None
):
    """
    Logout current user

    Invalidates the user's session.

    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        db: Database session

    Returns:
        Logout confirmation
    """
    try:
        # Get session token from request state (set by middleware)
        session_token = getattr(request.state, "session_token", None)

        if session_token:
            success = await auth_service.logout(session_token, db)
            if success:
                return LogoutResponse(message="Successfully logged out", success=True)

        return LogoutResponse(message="No active session found", success=False)

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
    request: MicrosoftTokenRequest,
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
        # Use the existing auth service to process the Microsoft token
        # This will validate the token, create/update user, and generate session
        result = await auth_service.process_microsoft_token(request.access_token, db)
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

@router.get("/profile", response_model=UserInfo)
async def get_user_profile(
    current_user: CurrentUser
):
    """
    Get user profile information

    Returns detailed user profile information for the authenticated user.

    Args:
        current_user: Current authenticated user from token

    Returns:
        Complete user profile information
    """
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        preferred_language=current_user.preferred_language,
        department=current_user.department,
        job_title=current_user.job_title,
        created_at=current_user.created_at
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