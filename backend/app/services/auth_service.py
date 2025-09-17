"""
Authentication service using Microsoft Azure AD with MSAL
Migrated from Django authentication system
"""
import msal
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import uuid
import httpx

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password
)
from app.models.user import User, UserSession

logger = logging.getLogger(__name__)

class AuthService:
    """
    Service for handling authentication with Microsoft Azure AD
    """

    def __init__(self):
        """Initialize MSAL confidential client application"""
        self.authority = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}"

        self.msal_app = msal.ConfidentialClientApplication(
            settings.AZURE_AD_CLIENT_ID,
            authority=self.authority,
            client_credential=settings.AZURE_AD_CLIENT_SECRET,
        )

        self.redirect_uri = settings.AZURE_AD_REDIRECT_URI
        self.scopes = ["User.Read", "openid", "profile", "email"]

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate Microsoft login URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for Microsoft login
        """
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state or str(uuid.uuid4())
        )
        return auth_url

    async def process_auth_callback(
        self,
        code: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process the authorization code from Microsoft callback

        Args:
            code: Authorization code from Microsoft
            db: Database session

        Returns:
            Dict containing user info and tokens
        """
        try:
            # Exchange authorization code for tokens
            result = self.msal_app.acquire_token_by_authorization_code(
                code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )

            if "error" in result:
                logger.error(f"MSAL error: {result.get('error_description', result['error'])}")
                raise ValueError(f"Authentication failed: {result['error']}")

            # Get user info from Microsoft Graph
            access_token = result["access_token"]
            user_info = await self._get_user_info(access_token)

            # Create or update user in database
            user = await self._create_or_update_user(db, user_info, result)

            # Create session
            session = await self._create_session(db, user, result)

            # Create JWT tokens
            jwt_access = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            jwt_refresh = create_refresh_token(
                data={"sub": str(user.id)}
            )

            return {
                "access_token": jwt_access,
                "refresh_token": jwt_refresh,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "display_name": user.display_name,
                    "is_admin": user.is_admin,
                    "preferred_language": user.preferred_language
                }
            }

        except Exception as e:
            logger.error(f"Authentication callback error: {e}")
            raise

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Microsoft Graph API

        Args:
            access_token: Microsoft access token

        Returns:
            User information from Microsoft Graph
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    async def _create_or_update_user(
        self,
        db: AsyncSession,
        user_info: Dict[str, Any],
        auth_result: Dict[str, Any]
    ) -> User:
        """
        Create a new user or update existing user

        Args:
            db: Database session
            user_info: User information from Microsoft
            auth_result: Authentication result from MSAL

        Returns:
            User model instance
        """
        microsoft_id = user_info.get("id")
        email = user_info.get("mail") or user_info.get("userPrincipalName", "")

        # Check if user exists
        stmt = select(User).where(
            (User.microsoft_id == microsoft_id) | (User.email == email)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update existing user
            user.microsoft_id = microsoft_id
            user.first_name = user_info.get("givenName", "")
            user.last_name = user_info.get("surname", "")
            user.preferred_name = user_info.get("displayName", "")
            user.job_title = user_info.get("jobTitle", "")
            user.department = user_info.get("department", "")
            user.last_login = datetime.now(timezone.utc)
        else:
            # Create new user
            username = email.split("@")[0] if email else f"user_{microsoft_id[:8]}"

            user = User(
                microsoft_id=microsoft_id,
                email=email,
                username=username,
                first_name=user_info.get("givenName", ""),
                last_name=user_info.get("surname", ""),
                preferred_name=user_info.get("displayName", ""),
                job_title=user_info.get("jobTitle", ""),
                department=user_info.get("department", ""),
                is_active=True,
                last_login=datetime.now(timezone.utc)
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)
        return user

    async def _create_session(
        self,
        db: AsyncSession,
        user: User,
        auth_result: Dict[str, Any]
    ) -> UserSession:
        """
        Create a new user session

        Args:
            db: Database session
            user: User model instance
            auth_result: Authentication result from MSAL

        Returns:
            UserSession model instance
        """
        # Deactivate old sessions
        stmt = update(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.is_active == True
        ).values(is_active=False)
        await db.execute(stmt)

        # Create new session
        session = UserSession(
            user_id=user.id,
            session_token=UserSession.generate_token(),
            microsoft_token=auth_result.get("access_token"),
            refresh_token=auth_result.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_EXPIRE_HOURS),
            is_active=True
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def refresh_token(
        self,
        refresh_token: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: JWT refresh token
            db: Database session

        Returns:
            New tokens and user info
        """
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")

        # Get user
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Create new tokens
        jwt_access = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        jwt_refresh = create_refresh_token(
            data={"sub": str(user.id)}
        )

        return {
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
            "token_type": "bearer"
        }

    async def logout(
        self,
        session_token: str,
        db: AsyncSession
    ) -> bool:
        """
        Logout user by deactivating session

        Args:
            session_token: Session token to deactivate
            db: Database session

        Returns:
            Success status
        """
        stmt = update(UserSession).where(
            UserSession.session_token == session_token
        ).values(is_active=False)

        result = await db.execute(stmt)
        await db.commit()

        return result.rowcount > 0

    async def get_current_user(
        self,
        token: str,
        db: AsyncSession
    ) -> Optional[User]:
        """
        Get current user from JWT token

        Args:
            token: JWT access token
            db: Database session

        Returns:
            User model instance or None
        """
        payload = verify_token(token, token_type="access")
        if not payload:
            return None

        user_id = payload.get("sub")

        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        return user if user and user.is_active else None

    async def process_microsoft_token(
        self,
        access_token: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process Microsoft access token from frontend (MSAL)

        This method is used when the frontend sends the Microsoft access token
        directly (as opposed to the authorization code flow).

        Args:
            access_token: Microsoft access token from MSAL frontend
            db: Database session

        Returns:
            Dictionary with access_token, refresh_token, user info and session_token
        """
        try:
            # Get user information from Microsoft Graph API
            user_info = await self._get_user_info(access_token)
            logger.info(f"Retrieved user info for: {user_info.get('mail', user_info.get('userPrincipalName'))}")

            # Create a mock auth_result for token exchange flow
            # Since we received the token directly, we don't have refresh_token from MSAL
            auth_result = {
                "access_token": access_token,
                "refresh_token": None  # Will be generated by our JWT system
            }

            # Create or update user in database
            user = await self._create_or_update_user(db, user_info, auth_result)

            # Create new session for the user
            session = await self._create_session(db, user, auth_result)

            # Create JWT tokens
            jwt_access = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            jwt_refresh = create_refresh_token(
                data={"sub": str(user.id)}
            )

            return {
                "access_token": jwt_access,
                "refresh_token": jwt_refresh,
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "display_name": user.display_name or user.preferred_name or f"{user.first_name} {user.last_name}".strip(),
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "preferred_language": user.preferred_language,
                    "department": user.department,
                    "job_title": user.job_title,
                    "created_at": user.created_at
                },
                "session_token": jwt_access  # Frontend expects this field
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Microsoft Graph API error: {e}")
            raise ValueError("Invalid Microsoft access token")
        except Exception as e:
            logger.error(f"Error processing Microsoft token: {e}")
            raise

    async def update_user_profile(
        self,
        user_id: int,
        profile_data: dict,
        db: AsyncSession
    ) -> User:
        """
        Update user profile information

        Args:
            user_id: User ID to update
            profile_data: Dictionary with profile fields to update
            db: Database session

        Returns:
            Updated user model
        """
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            # Update allowed fields
            allowed_fields = ['display_name', 'department', 'job_title']
            for field, value in profile_data.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)

            await db.commit()
            await db.refresh(user)
            return user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating user profile: {e}")
            raise

    async def update_language_preference(
        self,
        user_id: int,
        language: str,
        db: AsyncSession
    ) -> bool:
        """
        Update user language preference

        Args:
            user_id: User ID to update
            language: New language preference
            db: Database session

        Returns:
            Success status
        """
        try:
            stmt = update(User).where(User.id == user_id).values(
                preferred_language=language
            )
            result = await db.execute(stmt)
            await db.commit()

            return result.rowcount > 0

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating language preference: {e}")
            raise

# Singleton instance
auth_service = AuthService()