#!/usr/bin/env python3
"""
Debug script para testar a autenticação Microsoft
"""
import asyncio
import sys
import os
import logging

# Add the app directory to Python path
sys.path.insert(0, '/home/felipealbertuxd/knight-agent/backend')

from app.services.microsoft_token_validator import microsoft_token_validator
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_microsoft_config():
    """Test Microsoft configuration"""
    print("=== MICROSOFT AZURE AD CONFIGURATION ===")
    print(f"Client ID: {settings.AZURE_AD_CLIENT_ID[:10]}..." if settings.AZURE_AD_CLIENT_ID else "❌ NOT SET")
    print(f"Tenant ID: {settings.AZURE_AD_TENANT_ID[:10]}..." if settings.AZURE_AD_TENANT_ID else "❌ NOT SET")
    print(f"Client Secret: {'✅ SET' if settings.AZURE_AD_CLIENT_SECRET else '❌ NOT SET'}")
    print(f"Redirect URI: {settings.AZURE_AD_REDIRECT_URI}")
    print()

    # Test JWKS endpoint
    print("=== TESTING MICROSOFT JWKS ENDPOINT ===")
    try:
        jwks_uri = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        print(f"JWKS URI: {jwks_uri}")

        keys = await microsoft_token_validator.get_signing_keys()
        print(f"✅ Successfully fetched {len(keys)} Microsoft signing keys")

        for kid, key in list(keys.items())[:2]:  # Show first 2 keys
            print(f"   Key ID: {kid}")
            print(f"   Key Type: {key.get('kty')}")
            print(f"   Use: {key.get('use')}")
    except Exception as e:
        print(f"❌ Failed to fetch Microsoft keys: {e}")

    print()

async def test_token_validation():
    """Test token validation with a dummy token"""
    print("=== TESTING TOKEN VALIDATION ===")

    # This will fail but we can see the error details
    dummy_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjFMVE16YWtpaGlSbGFfOHoyQkVKVlhlV01xbyJ9.eyJ2ZXIiOiIyLjAiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vOTEyMmE3ZmYtOGM1ZC00MjE3LWI5ZTQtNzYzOTIzN2U3Mzk0L3YyLjAiLCJzdWIiOiJBQUFBQUFBQUFBQUFBQUFBQUFBQUFNTmVBRkVBQUFBQUFBQUFBQUFBQUE"

    try:
        result = await microsoft_token_validator.validate_token(dummy_token)
        if result:
            print("✅ Token validation passed")
            print(f"   Subject: {result.get('sub')}")
            print(f"   Issuer: {result.get('iss')}")
        else:
            print("❌ Token validation failed")
    except Exception as e:
        print(f"❌ Token validation error: {e}")

    print()

async def main():
    """Main debug function"""
    print("🔍 DEBUGGING MICROSOFT AUTHENTICATION")
    print("="*50)

    await test_microsoft_config()
    await test_token_validation()

    print("Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())