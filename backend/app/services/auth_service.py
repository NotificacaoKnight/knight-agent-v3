"""
Authentication service using Microsoft Azure AD with MSAL for FastAPI
"""
import msal
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import uuid
import httpx
import jwt
from cryptography.hazmat.primitives import serialization
import base64

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password
)
from app.core.admin_config import admin_service
from app.models.user import User, UserSession
from app.services.microsoft_token_validator import microsoft_token_validator
from app.services.msal_token_validator import msal_token_validator

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
        self._jwks_cache = {}  # Cache for Microsoft public keys

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

            # Create or update user in database first (without photo)
            user = await self._create_or_update_user(db, user_info, result, None)

            # Now get and save user profile picture with user ID
            profile_picture_path = await self._get_user_photo(access_token, user.id)
            if profile_picture_path:
                user.profile_picture = profile_picture_path
                await db.commit()
                await db.refresh(user)

            # Create session
            session = await self._create_session(db, user, result)

            # Create JWT tokens
            jwt_access = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            jwt_refresh, _ = create_refresh_token(
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
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "preferred_name": user.preferred_name,
                    "profile_picture": user.profile_picture,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "preferred_language": user.preferred_language,
                    "department": user.department,
                    "job_title": user.job_title,
                    "created_at": user.created_at
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

    async def _get_user_photo(self, access_token: str, user_id: Optional[int] = None) -> Optional[str]:
        """
        Get user profile picture from Microsoft Graph API and save to disk

        Args:
            access_token: Microsoft access token
            user_id: User ID for naming the file (optional, will be set after user creation)

        Returns:
            Profile picture path or None if not available
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/photo/$value",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if response.status_code == 200 and user_id:
                    # Save image to disk
                    import os
                    from pathlib import Path

                    # Determine file extension from content-type
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    extension = 'jpg'
                    if 'png' in content_type:
                        extension = 'png'
                    elif 'gif' in content_type:
                        extension = 'gif'
                    elif 'webp' in content_type:
                        extension = 'webp'

                    # Create file path
                    media_dir = Path("media/profile_pictures")
                    media_dir.mkdir(parents=True, exist_ok=True)

                    file_name = f"{user_id}.{extension}"
                    file_path = media_dir / file_name

                    # Save the image with better error handling
                    try:
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"Profile picture saved successfully: {file_path}")
                        # Return the relative path for storage in database
                        return f"/media/profile_pictures/{file_name}"
                    except PermissionError:
                        # Try with a timestamp suffix if permission denied
                        import time
                        timestamp = int(time.time())
                        file_name_alt = f"{user_id}_{timestamp}.{extension}"
                        file_path_alt = media_dir / file_name_alt
                        try:
                            with open(file_path_alt, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Profile picture saved with alternate name: {file_path_alt}")
                            return f"/media/profile_pictures/{file_name_alt}"
                        except Exception as alt_error:
                            logger.error(f"Failed to save profile picture even with alternate name: {alt_error}")
                            return None
                    except Exception as save_error:
                        logger.error(f"Failed to save profile picture: {save_error}")
                        return None
                elif response.status_code == 200:
                    # If no user_id yet, store temporarily (will be saved after user creation)
                    return response.content
                else:
                    logger.info("Profile picture not found for user")
                    return None
        except Exception as e:
            logger.warning(f"Failed to fetch user profile picture: {e}")
            return None

    async def _create_or_update_user(
        self,
        db: AsyncSession,
        user_info: Dict[str, Any],
        auth_result: Dict[str, Any],
        profile_picture: Optional[str] = None
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

        # Check if email should have admin privileges
        should_be_admin = await admin_service.is_admin_email(email, db)

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
            if profile_picture:
                user.profile_picture = profile_picture

            # Update admin status if changed
            if user.is_admin != should_be_admin:
                logger.info(f"Updating admin status for {email}: {user.is_admin} -> {should_be_admin}")
                user.is_admin = should_be_admin
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
                profile_picture=profile_picture,
                is_active=True,
                is_admin=should_be_admin,  # Set admin status for new user
                last_login=datetime.now(timezone.utc)
            )
            db.add(user)
            logger.info(f"Created new user {email} with admin={should_be_admin}")

        await db.commit()
        await db.refresh(user)
        return user

    async def _create_session(
        self,
        db: AsyncSession,
        user: User,
        auth_result: Dict[str, Any],
        user_agent: str = "",
        ip_address: str = ""
    ) -> UserSession:
        """
        Create a new user session with device fingerprinting and refresh token rotation

        Args:
            db: Database session
            user: User model instance
            auth_result: Authentication result from MSAL
            user_agent: Client user agent string
            ip_address: Client IP address

        Returns:
            UserSession model instance
        """
        from app.core.security import generate_device_fingerprint

        # Deactivate old sessions
        stmt = update(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.is_active == True
        ).values(is_active=False)
        await db.execute(stmt)

        # Generate JWT refresh token with rotation support
        jwt_refresh, token_family = create_refresh_token(
            data={"sub": str(user.id)}
        )

        # Generate device fingerprint
        device_fp = generate_device_fingerprint(user_agent, ip_address)

        # Create new session
        session = UserSession(
            user_id=user.id,
            session_token=UserSession.generate_token(),
            microsoft_token=auth_result.get("access_token"),
            refresh_token=jwt_refresh,
            refresh_token_family=token_family,
            device_fingerprint=device_fp,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_EXPIRE_HOURS),
            refresh_expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            is_active=True,
            refresh_count=0
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
        jwt_refresh, _ = create_refresh_token(
            data={"sub": str(user.id)}
        )

        return {
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
            "token_type": "bearer"
        }

    async def refresh_token_with_rotation(
        self,
        refresh_token: str,
        user_agent: str,
        ip_address: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Refresh access token with automatic token rotation and device fingerprinting

        Security features:
        - Rotates refresh token on every use (old token invalidated)
        - Validates device fingerprint to prevent token theft
        - Detects token reuse and invalidates entire token family
        - Tracks refresh count and timestamps for anomaly detection

        Args:
            refresh_token: JWT refresh token
            user_agent: Client user agent string
            ip_address: Client IP address
            db: Database session

        Returns:
            New tokens and user info

        Raises:
            ValueError: If token is invalid, expired, or reused
        """
        from app.core.security import (
            verify_device_fingerprint,
            generate_device_fingerprint,
            blacklist_token
        )

        # Verify refresh token
        payload = await verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise ValueError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        token_family = payload.get("family")
        token_jti = payload.get("jti")  # Unique token ID

        if not token_family or not token_jti:
            raise ValueError("Invalid refresh token format")

        # Get user and active session with this token family
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Find session with this token family
        session_stmt = select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.refresh_token_family == token_family,
            UserSession.is_active == True
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        if not session:
            # Token reuse detected! This token family was already used
            # Invalidate ALL sessions with this token family (security breach)
            logger.warning(
                f"SECURITY ALERT: Refresh token reuse detected for user {user.id}, "
                f"family {token_family}. Invalidating all sessions in family."
            )

            # Invalidate all sessions in this token family
            invalidate_stmt = update(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.refresh_token_family == token_family
            ).values(is_active=False)
            await db.execute(invalidate_stmt)
            await db.commit()

            # Blacklist the reused token
            await blacklist_token(refresh_token)

            raise ValueError("Token reuse detected. All sessions invalidated for security.")

        # Verify device fingerprint
        if session.device_fingerprint:
            if not verify_device_fingerprint(
                session.device_fingerprint,
                user_agent,
                ip_address
            ):
                logger.warning(
                    f"Device fingerprint mismatch for user {user.id}. "
                    f"Possible token theft attempt."
                )
                # Don't immediately invalidate - could be legitimate (user changed network/browser)
                # But log for monitoring
                # In stricter mode, you could invalidate here

        # Blacklist old refresh token (it's now consumed)
        await blacklist_token(refresh_token)

        # Create new tokens with SAME token family (rotation within family)
        jwt_access = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "session_id": session.id
            }
        )

        # Generate new refresh token in same family
        jwt_refresh, _ = create_refresh_token(
            data={"sub": str(user.id)},
            token_family=token_family  # Reuse same family for rotation tracking
        )

        # Update session with new refresh token and metadata
        session.refresh_token = jwt_refresh
        session.refresh_count += 1
        session.last_refresh_at = datetime.now(timezone.utc)
        session.last_activity = datetime.now(timezone.utc)

        # Update device fingerprint (in case user switched devices legitimately)
        session.device_fingerprint = generate_device_fingerprint(
            user_agent, ip_address
        )
        session.ip_address = ip_address
        session.user_agent = user_agent

        await db.commit()

        logger.info(
            f"Refresh token rotated for user {user.id}, "
            f"family {token_family}, count {session.refresh_count}"
        )

        return {
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username
            }
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

    async def logout_user(
        self,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Logout user by deactivating all their sessions

        Args:
            user_id: User ID to logout
            db: Database session

        Returns:
            Success status
        """
        stmt = update(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).values(is_active=False)

        result = await db.execute(stmt)
        await db.commit()

        return True  # Always return True for JWT-based logout

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
        payload = await verify_token(token, token_type="access")
        if not payload:
            return None

        user_id = payload.get("sub")

        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        return user if user and user.is_active else None

    async def _validate_microsoft_token(self, access_token: str) -> Dict[str, Any]:
        """
        Validate Microsoft access token with full signature verification

        Args:
            access_token: Microsoft access token to validate

        Returns:
            Decoded token payload if valid, empty dict otherwise
        """
        try:
            # Strategy 1: Try full signature validation
            decoded_token = await microsoft_token_validator.validate_token(access_token)

            if decoded_token:
                logger.info("✅ Token validated with signature verification")
                return decoded_token

            logger.warning("⚠️ Signature validation failed, trying Graph API validation")

            # Strategy 2: Use MSAL validation (recommended and secure)
            if settings.USE_MSAL_VALIDATION:
                logger.info("🔐 Trying MSAL-based validation as fallback")
                decoded_token = await msal_token_validator.validate_access_token(access_token)

                if decoded_token:
                    logger.info("✅ Token validated with MSAL (secure)")
                    return decoded_token

            # Strategy 3: Unsafe fallback (only if explicitly enabled)
            if settings.ALLOW_FALLBACK_VALIDATION:
                logger.warning("⚠️ Using unsafe fallback validation - NOT RECOMMENDED FOR PRODUCTION")

                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://graph.microsoft.com/v1.0/me",
                            headers={"Authorization": f"Bearer {access_token}"},
                            timeout=10.0
                        )

                        if response.status_code == 200:
                            logger.warning("⚠️ Token validated via Microsoft Graph API (fallback)")

                            # Decode without verification to get claims
                            import jwt
                            decoded_token = jwt.decode(
                                access_token,
                                options={"verify_signature": False}
                            )

                            # Validate basic claims manually
                            if decoded_token.get('tid') != settings.AZURE_AD_TENANT_ID:
                                logger.error("Invalid tenant in fallback validation")
                                return {}

                            # Add user info from Graph API
                            graph_data = response.json()
                            decoded_token["graph_validated"] = True
                            decoded_token["preferred_username"] = graph_data.get("userPrincipalName", "")
                            decoded_token["name"] = graph_data.get("displayName", "")

                            return decoded_token
                        else:
                            logger.error(f"Graph API validation failed: {response.status_code}")

                except Exception as graph_error:
                    logger.error(f"Graph API validation error: {graph_error}")

            logger.error("🚫 All validation methods failed - token rejected")
            return {}

        except Exception as e:
            logger.error(f"Error validating Microsoft token: {e}")
            return {}

    async def process_microsoft_id_token(
        self,
        id_token: str,
        access_token: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process Microsoft ID token + Access token (RECOMMENDED method)

        This method uses ID token for authentication and Access token for API calls.
        This is the secure and recommended approach for Microsoft authentication.

        Args:
            id_token: Microsoft ID token for authentication
            access_token: Microsoft access token for Graph API calls
            db: Database session

        Returns:
            Dictionary with access_token, refresh_token, user info and session_token
        """
        try:
            logger.info("🔐 Processing Microsoft ID token + Access token (SECURE)")

            # Validate ID token (this is what we use for authentication)
            id_token_payload = await msal_token_validator.validate_id_token(id_token)
            if not id_token_payload:
                raise ValueError("Invalid Microsoft ID token")

            logger.info("✅ ID token validated successfully")

            # Get user information from Microsoft Graph API using access token
            user_info = await self._get_user_info(access_token)
            logger.info(f"Retrieved user info for: {user_info.get('mail', user_info.get('userPrincipalName'))}")

            # Create a mock auth_result for token exchange flow
            auth_result = {
                "access_token": access_token,
                "refresh_token": None,  # Will be generated by our JWT system
                "id_token": id_token,
                "id_token_claims": id_token_payload
            }

            # Create or update user in database first (without photo)
            user = await self._create_or_update_user(db, user_info, auth_result, None)

            # Now get and save user profile picture with user ID
            profile_picture_path = await self._get_user_photo(access_token, user.id)
            if profile_picture_path:
                user.profile_picture = profile_picture_path
                await db.commit()
                await db.refresh(user)

            # Create new session for the user
            session = await self._create_session(db, user, auth_result)

            # Create JWT tokens
            jwt_access = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            jwt_refresh, _ = create_refresh_token(
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
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "preferred_name": user.preferred_name,
                    "profile_picture": user.profile_picture,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "preferred_language": user.preferred_language,
                    "department": user.department,
                    "job_title": user.job_title
                },
                "validation_method": "id_token",  # Indicate which method was used
                "authenticated_with": "microsoft_id_token"
            }

        except Exception as e:
            logger.error(f"Microsoft ID token processing error: {e}")
            raise

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
            # First validate the Microsoft token with signature verification
            token_payload = await self._validate_microsoft_token(access_token)
            if not token_payload:
                raise ValueError("Invalid Microsoft access token")

            # Get user information from Microsoft Graph API
            user_info = await self._get_user_info(access_token)
            logger.info(f"Retrieved user info for: {user_info.get('mail', user_info.get('userPrincipalName'))}")

            # Create a mock auth_result for token exchange flow
            # Since we received the token directly, we don't have refresh_token from MSAL
            auth_result = {
                "access_token": access_token,
                "refresh_token": None  # Will be generated by our JWT system
            }

            # Create or update user in database first (without photo)
            user = await self._create_or_update_user(db, user_info, auth_result, None)

            # Now get and save user profile picture with user ID
            profile_picture_path = await self._get_user_photo(access_token, user.id)
            if profile_picture_path:
                user.profile_picture = profile_picture_path
                await db.commit()
                await db.refresh(user)

            # Create new session for the user
            session = await self._create_session(db, user, auth_result)

            # Create JWT tokens
            jwt_access = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            jwt_refresh, _ = create_refresh_token(
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
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "preferred_name": user.preferred_name,
                    "profile_picture": user.profile_picture,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "preferred_language": user.preferred_language,
                    "department": user.department,
                    "job_title": user.job_title,
                    "created_at": user.created_at
                }
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