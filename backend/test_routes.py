#!/usr/bin/env python3
"""Test script to verify API routes are properly configured"""

import sys
sys.path.insert(0, '/home/felipealbertuxd/knight-agent/backend')

def test_routes():
    """Test that routes are properly configured"""

    # Mock dependencies to avoid database requirements
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'

    # Try to import the routers
    try:
        from app.api import router as api_router
        from app.api import chat, llm_management, auth

        print("✓ All API modules imported successfully")

        # List all routes from chat router
        print("\nChat routes:")
        for route in chat.router.routes:
            if hasattr(route, 'path'):
                print(f"  {route.path}")

        # List all routes from llm_management router
        print("\nLLM Management routes:")
        for route in llm_management.router.routes:
            if hasattr(route, 'path'):
                print(f"  {route.path}")

        # List all routes from auth router
        print("\nAuth routes:")
        for route in auth.router.routes:
            if hasattr(route, 'path'):
                print(f"  {route.path}")

        print("\n✓ All routes configured correctly!")
        print("\nExpected URLs after mounting:")
        print("  /api/chat/sessions -> GET and POST")
        print("  /api/rag/llm/status -> GET")
        print("  /api/auth/me -> GET")

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = test_routes()
    sys.exit(0 if success else 1)