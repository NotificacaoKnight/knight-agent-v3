#!/usr/bin/env python3
"""
JWT Token Validation Debug Script
Tests Microsoft token validation independently to identify issues
"""
import asyncio
import sys
import os
import jwt
import json
import base64
import httpx
from datetime import datetime, timezone
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.services.microsoft_token_validator import microsoft_token_validator

class TokenDebugger:
    """Debug Microsoft JWT token validation"""

    def __init__(self):
        self.tenant_id = settings.AZURE_AD_TENANT_ID
        self.client_id = settings.AZURE_AD_CLIENT_ID

    def decode_token_parts(self, token: str) -> dict:
        """Decode token parts without verification"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {"error": f"Invalid token: {len(parts)} parts instead of 3"}

            # Decode header
            header_bytes = base64.urlsafe_b64decode(parts[0] + '=' * (4 - len(parts[0]) % 4))
            header = json.loads(header_bytes)

            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(parts[1] + '=' * (4 - len(parts[1]) % 4))
            payload = json.loads(payload_bytes)

            return {
                "header": header,
                "payload": payload,
                "signature_length": len(parts[2])
            }
        except Exception as e:
            return {"error": f"Failed to decode: {e}"}

    async def fetch_microsoft_keys(self) -> dict:
        """Fetch Microsoft signing keys directly"""
        try:
            jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch keys: {e}"}

    def test_key_conversion(self, jwk: dict) -> dict:
        """Test JWK to PEM conversion"""
        try:
            # Use the same method as our validator
            public_key = microsoft_token_validator._get_rsa_key_from_jwk(jwk)
            return {
                "success": True,
                "pem_length": len(public_key),
                "pem_preview": public_key[:100] + "..."
            }
        except Exception as e:
            return {"error": f"Key conversion failed: {e}"}

    async def test_microsoft_validation(self, token: str) -> dict:
        """Test validation using Microsoft's approach"""
        try:
            # First, try our current validator
            our_result = await microsoft_token_validator.validate_token(token)

            # Also try direct PyJWT with minimal validation
            unverified = jwt.decode(token, options={"verify_signature": False})

            return {
                "our_validator_success": our_result is not None,
                "our_validator_result": "Token validated" if our_result else "Token failed",
                "unverified_claims": {
                    "aud": unverified.get("aud"),
                    "iss": unverified.get("iss"),
                    "exp": unverified.get("exp"),
                    "iat": unverified.get("iat"),
                    "tid": unverified.get("tid"),
                    "sub": unverified.get("sub", "N/A")[:20] + "...",
                    "appid": unverified.get("appid", "N/A")
                }
            }
        except Exception as e:
            return {"error": f"Validation test failed: {e}"}

    async def test_alternative_libraries(self, token: str) -> dict:
        """Test with alternative JWT libraries"""
        results = {}

        # Test with different PyJWT options
        try:
            # Get token parts
            decoded_parts = self.decode_token_parts(token)
            if "error" in decoded_parts:
                return {"error": decoded_parts["error"]}

            header = decoded_parts["header"]
            payload = decoded_parts["payload"]

            # Get the signing key
            keys_data = await self.fetch_microsoft_keys()
            if "error" in keys_data:
                return {"microsoft_keys_error": keys_data["error"]}

            # Find the right key
            kid = header.get("kid")
            key_data = None
            for key in keys_data.get("keys", []):
                if key.get("kid") == kid:
                    key_data = key
                    break

            if not key_data:
                return {"error": f"Key {kid} not found in Microsoft keys"}

            # Try different approaches
            public_key = microsoft_token_validator._get_rsa_key_from_jwk(key_data)

            # Test 1: Minimal validation
            try:
                minimal = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    options={
                        "verify_signature": True,
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_exp": False
                    }
                )
                results["minimal_validation"] = "SUCCESS"
            except Exception as e:
                results["minimal_validation"] = f"FAILED: {e}"

            # Test 2: With audience
            try:
                with_aud = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    audience=payload.get("aud"),
                    options={
                        "verify_signature": True,
                        "verify_aud": True,
                        "verify_iss": False,
                        "verify_exp": False
                    }
                )
                results["with_audience"] = "SUCCESS"
            except Exception as e:
                results["with_audience"] = f"FAILED: {e}"

            # Test 3: With issuer
            try:
                with_iss = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    issuer=payload.get("iss"),
                    options={
                        "verify_signature": True,
                        "verify_aud": False,
                        "verify_iss": True,
                        "verify_exp": False
                    }
                )
                results["with_issuer"] = "SUCCESS"
            except Exception as e:
                results["with_issuer"] = f"FAILED: {e}"

            return results

        except Exception as e:
            return {"error": f"Alternative test failed: {e}"}

async def main():
    """Main debug function"""
    print("🔍 JWT Token Validation Debug Script")
    print("=====================================\n")

    debugger = TokenDebugger()

    # Check configuration
    print(f"Tenant ID: {debugger.tenant_id}")
    print(f"Client ID: {debugger.client_id}")
    print()

    # Get a sample token from logs (you'll need to paste a real token here)
    # This is just a placeholder - replace with actual token from logs
    sample_token = input("Paste a real Microsoft token from the logs (or press Enter to skip): ").strip()

    if not sample_token:
        print("No token provided. Exiting.")
        return

    print("🔍 Analyzing token structure...")
    token_parts = debugger.decode_token_parts(sample_token)
    print(json.dumps(token_parts, indent=2))
    print()

    print("🔍 Fetching Microsoft signing keys...")
    keys_data = await debugger.fetch_microsoft_keys()
    if "error" in keys_data:
        print(f"❌ {keys_data['error']}")
        return

    print(f"✅ Found {len(keys_data.get('keys', []))} signing keys")
    print()

    if "header" in token_parts:
        kid = token_parts["header"].get("kid")
        print(f"🔍 Testing key conversion for kid: {kid}")

        # Find the key
        key_data = None
        for key in keys_data.get("keys", []):
            if key.get("kid") == kid:
                key_data = key
                break

        if key_data:
            conversion_result = debugger.test_key_conversion(key_data)
            print(json.dumps(conversion_result, indent=2))
            print()
        else:
            print(f"❌ Key {kid} not found")
            return

    print("🔍 Testing Microsoft validation...")
    validation_result = await debugger.test_microsoft_validation(sample_token)
    print(json.dumps(validation_result, indent=2))
    print()

    print("🔍 Testing alternative validation approaches...")
    alternative_result = await debugger.test_alternative_libraries(sample_token)
    print(json.dumps(alternative_result, indent=2))
    print()

    print("✅ Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())