"""
Test document upload functionality
"""
import asyncio
import aiofiles
from httpx import AsyncClient
import json

async def test_upload():
    """Test document upload with authentication"""

    # First, we need to get a valid session token
    # For testing, we'll create a test user session
    from app.core.database import get_async_db
    from app.models.user import User, UserSession
    from datetime import datetime, timedelta
    import secrets

    # Create a test session
    async for db in get_async_db():
        # Check if test user exists, if not create one
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "test@knight.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="test@knight.com",
                username="testuser",
                first_name="Test",
                last_name="User",
                microsoft_id="test-microsoft-id",
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Create a session
        session_token = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        db.add(session)
        await db.commit()
        break

    print(f"Created test session: {session_token}")

    # Now test the upload
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Read the test file
        with open("test_document.txt", "rb") as f:
            files = {
                "file": ("test_document.txt", f, "text/plain")
            }
            data = {
                "title": "Documento de Teste",
                "enable_ocr": "false",
                "language": "pt",
                "tags": "teste,rag,knight"
            }

            # Send the upload request
            response = await client.post(
                "/api/documents/upload",
                files=files,
                data=data,
                cookies={"session_token": session_token}
            )

            print(f"Upload response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Upload successful: {json.dumps(result, indent=2)}")
                document_id = result.get("id")

                # Wait a bit for processing
                await asyncio.sleep(2)

                # Check document status
                status_response = await client.get(
                    f"/api/documents/{document_id}",
                    cookies={"session_token": session_token}
                )

                if status_response.status_code == 200:
                    print(f"Document status: {json.dumps(status_response.json(), indent=2)}")
            else:
                print(f"Upload failed: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_upload())