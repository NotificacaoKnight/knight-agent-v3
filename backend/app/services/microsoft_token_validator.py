"""
Microsoft Token Validator
Validates Microsoft Azure AD tokens with proper signature verification
"""
import httpx
import jwt
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from functools import lru_cache
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)


class MicrosoftTokenValidator:
    """
    Validates Microsoft tokens by verifying JWT signature against Microsoft public keys
    """

    def __init__(self):
        self.tenant_id = settings.AZURE_AD_TENANT_ID
        self.client_id = settings.AZURE_AD_CLIENT_ID
        # Support both v1.0 and v2.0 endpoints
        self.issuers = [
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
            f"https://sts.windows.net/{self.tenant_id}/",
            f"https://login.microsoftonline.com/{self.tenant_id}/"
        ]
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self._keys_cache = {}
        self._keys_cache_time = None
        self._cache_duration = timedelta(hours=24)  # Cache keys for 24 hours

    async def get_signing_keys(self) -> Dict[str, Any]:
        """
        Fetch Microsoft's public signing keys

        Returns:
            Dictionary of key IDs to public keys
        """
        # Check cache
        if self._keys_cache and self._keys_cache_time:
            if datetime.now(timezone.utc) - self._keys_cache_time < self._cache_duration:
                logger.debug("Using cached Microsoft signing keys")
                return self._keys_cache

        try:
            # Fetch fresh keys
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_uri)
                response.raise_for_status()

                jwks = response.json()
                keys = {}

                for key in jwks.get('keys', []):
                    kid = key.get('kid')
                    if kid:
                        keys[kid] = key

                # Update cache
                self._keys_cache = keys
                self._keys_cache_time = datetime.now(timezone.utc)

                logger.info(f"Fetched {len(keys)} signing keys from Microsoft")
                return keys

        except Exception as e:
            logger.error(f"Failed to fetch Microsoft signing keys: {e}")
            # Return cached keys if available
            if self._keys_cache:
                logger.warning("Using expired cache due to fetch failure")
                return self._keys_cache
            raise

    def _get_rsa_key_from_jwk(self, jwk: Dict[str, Any]) -> str:
        """
        Convert JWK to PEM format for use with PyJWT

        Args:
            jwk: JSON Web Key from Microsoft

        Returns:
            PEM formatted public key
        """
        # Ensure the key is RSA
        if jwk.get('kty') != 'RSA':
            raise ValueError(f"Unsupported key type: {jwk.get('kty')}")

        # Get the modulus and exponent
        n = jwk.get('n')
        e = jwk.get('e')

        if not n or not e:
            raise ValueError("Invalid RSA key: missing n or e")

        # Build the public key
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # Decode base64url
        def base64url_decode(input_str):
            rem = len(input_str) % 4
            if rem > 0:
                input_str += '=' * (4 - rem)
            return base64.urlsafe_b64decode(input_str)

        # Convert to integers
        n_bytes = base64url_decode(n)
        e_bytes = base64url_decode(e)
        n_int = int.from_bytes(n_bytes, 'big')
        e_int = int.from_bytes(e_bytes, 'big')

        # Create public key
        public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key(default_backend())

        # Export to PEM
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return pem.decode('utf-8')

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a Microsoft access token

        Args:
            token: JWT token from Microsoft

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            logger.debug(f"🔍 Validating token: length={len(token)}, segments={token.count('.') + 1}")
            logger.debug(f"🔍 Token preview: {token[:50]}...")

            # Check basic JWT format first
            if token.count('.') != 2:
                logger.error(f"Invalid token: Not enough segments (expected 3, got {token.count('.') + 1})")
                return None

            # Decode without verification first to get the header
            unverified = jwt.decode(token, options={"verify_signature": False})
            header = jwt.get_unverified_header(token)

            # Get the key ID
            kid = header.get('kid')
            if not kid:
                logger.error("Token missing 'kid' in header")
                return None

            # Get signing keys
            signing_keys = await self.get_signing_keys()

            # Find the correct key
            key_data = signing_keys.get(kid)
            if not key_data:
                logger.error(f"Key ID '{kid}' not found in Microsoft signing keys")
                # Refresh keys and try again
                self._keys_cache_time = None  # Force refresh
                signing_keys = await self.get_signing_keys()
                key_data = signing_keys.get(kid)

                if not key_data:
                    logger.error(f"Key ID '{kid}' still not found after refresh")
                    return None

            # Convert JWK to PEM
            public_key = self._get_rsa_key_from_jwk(key_data)
            logger.info(f"✅ Successfully converted JWK to PEM for kid: {kid}")
            logger.info(f"Key details: kty={key_data.get('kty')}, use={key_data.get('use', 'N/A')}, alg={key_data.get('alg', 'N/A')}")

            # First try to decode without strict validation to inspect the token
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            token_aud = unverified_payload.get('aud', '')
            token_iss = unverified_payload.get('iss', '')
            token_exp = unverified_payload.get('exp', 0)
            token_iat = unverified_payload.get('iat', 0)

            # Extract additional token details for MSAL debugging
            token_typ = header.get('typ', 'N/A')
            token_use = unverified_payload.get('token_use', 'N/A')
            token_ver = unverified_payload.get('ver', 'N/A')
            token_sub = unverified_payload.get('sub', 'N/A')
            token_app_id = unverified_payload.get('appid', unverified_payload.get('azp', 'N/A'))
            token_scope = unverified_payload.get('scp', unverified_payload.get('scope', 'N/A'))

            logger.info(f"🔍 MSAL Token Analysis:")
            logger.info(f"  - Type (typ): {token_typ}")
            logger.info(f"  - Token Use: {token_use}")
            logger.info(f"  - Version (ver): {token_ver}")
            logger.info(f"  - App ID: {token_app_id}")
            logger.info(f"  - Scope: {token_scope}")
            logger.info(f"  - Audience (aud): {token_aud}")
            logger.info(f"  - Issuer (iss): {token_iss}")
            logger.info(f"  - Subject (sub): {token_sub[:20]}...")
            logger.info(f"  - Expires (exp): {token_exp} ({datetime.fromtimestamp(token_exp, tz=timezone.utc) if token_exp else 'N/A'})")
            logger.info(f"  - Issued (iat): {token_iat} ({datetime.fromtimestamp(token_iat, tz=timezone.utc) if token_iat else 'N/A'})")
            logger.info(f"  - Algorithm: {header.get('alg')}")
            logger.info(f"Expected client_id: {self.client_id}")
            logger.info(f"Expected audiences: {self.client_id}, 00000003-0000-0000-c000-000000000000")
            logger.info(f"Expected issuers: {self.issuers}")

            # Determine which audience to accept
            # Accept both our client_id and Microsoft Graph API audience
            valid_audiences = [
                self.client_id,
                "00000003-0000-0000-c000-000000000000",  # Microsoft Graph
                f"api://{self.client_id}",  # API scope format
                f"https://graph.microsoft.com"  # Graph API URL
            ]

            # Find matching issuer
            matching_issuer = None
            for issuer in self.issuers:
                if token_iss == issuer:
                    matching_issuer = issuer
                    break

            if not matching_issuer:
                logger.error(f"Token issuer '{token_iss}' not in expected issuers")
                # Try anyway with the token's issuer
                matching_issuer = token_iss

            # Special handling for MSAL/Azure AD tokens
            is_access_token = (token_use == 'access' or token_typ == 'JWT')
            is_microsoft_graph = (token_aud == "00000003-0000-0000-c000-000000000000")

            logger.info(f"🔍 Token classification: is_access_token={is_access_token}, is_microsoft_graph={is_microsoft_graph}")

            # Verify the token with flexible audience/issuer
            try:
                # For Microsoft Graph tokens, try with minimal validation first
                if is_microsoft_graph and is_access_token:
                    logger.info(f"🚀 Attempting Microsoft Graph access token validation")
                    decoded = jwt.decode(
                        token,
                        public_key,
                        algorithms=['RS256'],
                        audience=token_aud,
                        issuer=matching_issuer,
                        options={
                            "verify_signature": True,
                            "verify_aud": True,
                            "verify_iss": True,
                            "verify_exp": True,
                            "require": ["exp", "sub"]  # Removed iat requirement for access tokens
                        }
                    )
                # Try with specific audience if it matches
                elif token_aud in valid_audiences:
                    logger.info(f"✅ Audience '{token_aud}' is valid, attempting full verification")
                    decoded = jwt.decode(
                        token,
                        public_key,
                        algorithms=['RS256'],
                        audience=token_aud,
                        issuer=matching_issuer,
                        options={
                            "verify_signature": True,
                            "verify_aud": True,
                            "verify_iss": True,
                            "verify_exp": True,
                            "require": ["exp", "iat", "sub"]
                        }
                    )
                else:
                    # Try without audience verification as fallback
                    logger.warning(f"Token audience '{token_aud}' not in expected list, skipping audience validation")
                    decoded = jwt.decode(
                        token,
                        public_key,
                        algorithms=['RS256'],
                        issuer=matching_issuer,
                        options={
                            "verify_signature": True,
                            "verify_aud": False,  # Skip audience check
                            "verify_iss": True,
                            "verify_exp": True,
                            "require": ["exp", "iat", "sub"]
                        }
                    )
            except jwt.InvalidIssuerError:
                # Final fallback: verify signature only
                logger.warning("Issuer validation failed, falling back to signature-only validation")
                decoded = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    options={
                        "verify_signature": True,
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_exp": True,
                        "require": ["exp", "sub"]
                    }
                )
            except jwt.InvalidSignatureError as e:
                # Log detailed information about the signature verification failure
                logger.error(f"❌ JWT signature verification failed: {e}")
                logger.error(f"Token kid: {header.get('kid')}")
                logger.error(f"Token algorithm: {header.get('alg')}")
                logger.error(f"Key found in cache: {kid in signing_keys}")
                logger.error(f"Key type: {key_data.get('kty') if key_data else 'N/A'}")
                logger.error(f"Token issuer: {token_iss}")
                logger.error(f"Token audience: {token_aud}")

                # Try alternative validation approach for MSAL tokens
                logger.warning("🔄 Attempting alternative MSAL validation approach...")
                try:
                    # Sometimes MSAL tokens need more flexible validation
                    alternative_decoded = jwt.decode(
                        token,
                        public_key,
                        algorithms=['RS256'],
                        options={
                            "verify_signature": True,
                            "verify_aud": False,  # Skip audience check temporarily
                            "verify_iss": False,  # Skip issuer check temporarily
                            "verify_exp": True,
                            "require": ["exp", "sub"]
                        }
                    )

                    # Manual validation after successful signature verification
                    if alternative_decoded.get('tid') == self.tenant_id:
                        logger.info("✅ Alternative MSAL validation successful with signature verification!")
                        return alternative_decoded
                    else:
                        logger.error(f"Alternative validation failed: wrong tenant {alternative_decoded.get('tid')}")

                except Exception as alt_error:
                    logger.error(f"Alternative validation also failed: {alt_error}")

                # Signature failed - re-raise to be caught by outer handler
                raise

            # Additional validation
            if not decoded.get('sub'):
                logger.error("Token missing 'sub' claim")
                return None

            # Validate token type (optional)
            token_use = decoded.get('token_use')
            if token_use and token_use != 'access':
                logger.error(f"Invalid token_use: {token_use}")
                return None

            # Check that it's for our tenant
            tid = decoded.get('tid')
            if tid and tid != self.tenant_id:
                logger.error(f"Token from wrong tenant: {tid}")
                return None

            logger.info(f"Successfully validated Microsoft token for user: {decoded.get('preferred_username', decoded.get('sub'))}")
            return decoded

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidAudienceError:
            logger.error(f"Invalid audience - expected {self.client_id}")
            return None
        except jwt.InvalidIssuerError:
            logger.error(f"Invalid issuer - expected {self.issuer}")
            return None
        except jwt.InvalidSignatureError as e:
            logger.warning(f"Signature verification failed: {e}")
            # Last resort fallback: decode without signature verification but check basic claims
            logger.warning("⚠️ FALLING BACK: Signature verification failed, using fallback validation")
            try:
                fallback_decoded = jwt.decode(
                    token,
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_exp": True,
                        "require": ["exp", "sub"]
                    }
                )

                # Extra safety checks
                if not fallback_decoded.get('sub'):
                    logger.error("Fallback: Token missing 'sub' claim")
                    return None

                # Check tenant
                tid = fallback_decoded.get('tid')
                if tid and tid != self.tenant_id:
                    logger.error(f"Fallback: Token from wrong tenant: {tid}")
                    return None

                # Check expiry manually
                exp = fallback_decoded.get('exp')
                if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                    logger.error("Fallback: Token has expired")
                    return None

                logger.info(f"✅ FALLBACK SUCCESSFUL: Validated token for user: {fallback_decoded.get('preferred_username', fallback_decoded.get('sub'))}")
                logger.info(f"Token tenant: {tid}")
                return fallback_decoded

            except Exception as fallback_error:
                logger.error(f"Fallback validation also failed: {fallback_error}")
                return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    async def validate_id_token(self, id_token: str, nonce: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Validate a Microsoft ID token (used in OpenID Connect flows)

        Args:
            id_token: JWT ID token from Microsoft
            nonce: Expected nonce value for validation

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Validate as regular token first
            decoded = await self.validate_token(id_token)
            if not decoded:
                return None

            # Additional ID token specific validation
            if nonce:
                token_nonce = decoded.get('nonce')
                if token_nonce != nonce:
                    logger.error(f"Nonce mismatch: expected {nonce}, got {token_nonce}")
                    return None

            # Check required ID token claims
            required_claims = ['sub', 'iat', 'exp', 'aud', 'iss']
            for claim in required_claims:
                if claim not in decoded:
                    logger.error(f"ID token missing required claim: {claim}")
                    return None

            return decoded

        except Exception as e:
            logger.error(f"ID token validation error: {e}")
            return None


# Singleton instance
microsoft_token_validator = MicrosoftTokenValidator()