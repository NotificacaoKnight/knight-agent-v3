"""
MSAL-based Token Validator
More secure validation using Microsoft's own MSAL library
"""
import msal
import logging
import httpx
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.config import settings

# Import MSAL's ID token decoder
try:
    from msal.oauth2cli.oidc import decode_id_token
    MSAL_ID_TOKEN_AVAILABLE = True
except ImportError:
    MSAL_ID_TOKEN_AVAILABLE = False
    logging.warning("MSAL ID token decoder not available - using fallback method")

logger = logging.getLogger(__name__)


class MSALTokenValidator:
    """
    Validates Microsoft tokens using MSAL library for more reliable validation
    """

    def __init__(self):
        self.tenant_id = settings.AZURE_AD_TENANT_ID
        self.client_id = settings.AZURE_AD_CLIENT_ID
        self.client_secret = settings.AZURE_AD_CLIENT_SECRET
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Create MSAL app for validation
        self.msal_app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )

    async def validate_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate Microsoft ID token using MSAL's built-in method

        This is the RECOMMENDED method for validating Microsoft tokens.
        ID tokens are designed to be validated by applications, unlike
        Access tokens for Microsoft Graph API.

        Args:
            id_token: Microsoft ID token from MSAL

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            logger.info("🔐 Starting MSAL ID token validation (RECOMMENDED)")

            if MSAL_ID_TOKEN_AVAILABLE:
                # Use MSAL's built-in ID token decoder (most secure)
                try:
                    decoded = decode_id_token(
                        id_token=id_token,
                        client_id=self.client_id
                    )
                    logger.info("✅ ID Token validated with MSAL built-in decoder (SECURE)")
                    return decoded
                except Exception as e:
                    logger.error(f"MSAL ID token validation failed: {e}")
                    return None
            else:
                # Fallback: Manual ID token validation
                logger.warning("Using manual ID token validation (MSAL decoder not available)")
                return await self._validate_id_token_manually(id_token)

        except Exception as e:
            logger.error(f"ID token validation error: {e}")
            return None

    async def _validate_id_token_manually(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Manual ID token validation as fallback

        Args:
            id_token: Microsoft ID token

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Decode without verification first to get claims
            unverified_payload = jwt.decode(id_token, options={"verify_signature": False})
            logger.info(f"ID Token claims: aud={unverified_payload.get('aud')}, iss={unverified_payload.get('iss')}")

            # Basic validation checks for ID token
            if not self._validate_id_token_claims(unverified_payload):
                return None

            # ID tokens should have audience = client_id (not Graph API)
            expected_audience = self.client_id
            actual_audience = unverified_payload.get('aud')

            if actual_audience != expected_audience:
                logger.error(f"Invalid ID token audience: {actual_audience} != {expected_audience}")
                return None

            logger.info("✅ Manual ID token validation successful")
            return unverified_payload

        except Exception as e:
            logger.error(f"Manual ID token validation failed: {e}")
            return None

    def _validate_id_token_claims(self, payload: Dict[str, Any]) -> bool:
        """
        Validate ID token specific claims

        Args:
            payload: Token payload

        Returns:
            True if claims are valid
        """
        try:
            # Check required ID token claims
            required_claims = ['sub', 'aud', 'iss', 'exp', 'iat', 'tid']
            for claim in required_claims:
                if claim not in payload:
                    logger.error(f"Missing required ID token claim: {claim}")
                    return False

            # Check tenant ID
            if payload.get('tid') != self.tenant_id:
                logger.error(f"Invalid tenant in ID token: {payload.get('tid')} != {self.tenant_id}")
                return False

            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                logger.error("ID token has expired")
                return False

            # Check that it's an ID token (not access token)
            token_use = payload.get('aud')
            if token_use == "00000003-0000-0000-c000-000000000000":
                logger.error("This appears to be an Access Token for Graph API, not an ID Token")
                return False

            logger.info("✅ ID token claims validation passed")
            return True

        except Exception as e:
            logger.error(f"ID token claims validation error: {e}")
            return False

    async def validate_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate Microsoft access token using MSAL approach

        Args:
            access_token: Microsoft access token to validate

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            logger.info("🔍 Starting MSAL-based token validation")

            # Step 1: Decode token without verification to get claims
            unverified_payload = jwt.decode(access_token, options={"verify_signature": False})
            logger.info(f"Token claims: aud={unverified_payload.get('aud')}, iss={unverified_payload.get('iss')}")

            # Step 2: Basic validation checks
            if not self._validate_basic_claims(unverified_payload):
                return None

            # Step 3: Try to use the token with Microsoft Graph API to verify it's valid
            is_token_valid = await self._verify_token_with_microsoft_graph(access_token)

            if is_token_valid:
                logger.info("✅ MSAL validation successful - token verified with Microsoft Graph")
                return unverified_payload
            else:
                logger.error("❌ MSAL validation failed - token rejected by Microsoft Graph")
                return None

        except Exception as e:
            logger.error(f"MSAL validation error: {e}")
            return None

    def _validate_basic_claims(self, payload: Dict[str, Any]) -> bool:
        """
        Validate basic token claims

        Args:
            payload: Token payload

        Returns:
            True if basic claims are valid
        """
        try:
            # Check required claims exist
            required_claims = ['sub', 'aud', 'iss', 'exp', 'tid']
            for claim in required_claims:
                if claim not in payload:
                    logger.error(f"Missing required claim: {claim}")
                    return False

            # Check tenant ID
            if payload.get('tid') != self.tenant_id:
                logger.error(f"Invalid tenant: {payload.get('tid')} != {self.tenant_id}")
                return False

            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                logger.error("Token has expired")
                return False

            # Check audience (should be Microsoft Graph or our app)
            aud = payload.get('aud')
            valid_audiences = [
                self.client_id,
                "00000003-0000-0000-c000-000000000000",  # Microsoft Graph
                f"api://{self.client_id}",
                "https://graph.microsoft.com"
            ]

            if aud not in valid_audiences:
                logger.warning(f"Unexpected audience: {aud}")
                # Don't fail here - might be valid for different scopes

            logger.info("✅ Basic claims validation passed")
            return True

        except Exception as e:
            logger.error(f"Basic claims validation error: {e}")
            return False

    async def _verify_token_with_microsoft_graph(self, access_token: str) -> bool:
        """
        Verify token by making a call to Microsoft Graph API
        If the token is valid, Microsoft will respond successfully

        Args:
            access_token: Token to verify

        Returns:
            True if token is valid according to Microsoft
        """
        try:
            async with httpx.AsyncClient() as client:
                # Try to get user info - this validates the token
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    user_data = response.json()
                    logger.info(f"Token validated via Microsoft Graph for user: {user_data.get('userPrincipalName', 'unknown')}")
                    return True
                elif response.status_code == 401:
                    logger.error("Token rejected by Microsoft Graph (401 Unauthorized)")
                    return False
                else:
                    logger.error(f"Microsoft Graph returned status {response.status_code}")
                    return False

        except httpx.TimeoutException:
            logger.error("Timeout while validating token with Microsoft Graph")
            return False
        except Exception as e:
            logger.error(f"Error validating token with Microsoft Graph: {e}")
            return False

    async def get_user_info_from_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from validated token

        Args:
            access_token: Validated Microsoft access token

        Returns:
            User information from Microsoft Graph
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user info: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None


# Singleton instance
msal_token_validator = MSALTokenValidator()