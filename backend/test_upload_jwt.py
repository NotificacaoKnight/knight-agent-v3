"""
Test document upload with proper JWT authentication
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta, timezone

async def test_upload_with_jwt():
    """Test document upload with JWT authentication"""

    # Import necessary modules
    from app.core.database import get_async_db
    from app.models.user import User
    from app.core.security import create_access_token
    from sqlalchemy import select

    # Get or create test user
    async for db in get_async_db():
        # Check if test user exists
        result = await db.execute(select(User).where(User.email == "test@knight.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="test@knight.com",
                username="testuser",
                first_name="Test",
                last_name="User",
                microsoft_id="test-microsoft-id",
                is_active=True,
                is_admin=True  # Make admin for testing
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        print(f"User ID: {user.id}")
        break

    # Create JWT access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    print(f"Access token created")

    # Test the upload with JWT authentication
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # First test authentication
        me_response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if me_response.status_code == 200:
            print(f"Authentication successful: {me_response.json()['username']}")
        else:
            print(f"Authentication failed: {me_response.text}")
            return

        # Read the test file and upload
        with open("test_document.txt", "rb") as f:
            files = {
                "file": ("test_document.txt", f, "text/plain")
            }
            data = {
                "title": "Documento de Teste RAG",
                "enable_ocr": "false",
                "language": "pt",
                "tags": "teste,rag,knight,processamento"
            }

            # Send upload request with Bearer token
            response = await client.post(
                "/api/documents/upload",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            print(f"\nUpload response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"Upload successful!")
                print(f"Document ID: {result.get('id')}")
                print(f"Title: {result.get('title')}")
                print(f"Status: {result.get('status')}")

                document_id = result.get("id")

                # Wait for processing
                print("\nWaiting for document processing...")
                await asyncio.sleep(3)

                # Check document status
                status_response = await client.get(
                    f"/api/documents/{document_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if status_response.status_code == 200:
                    doc_data = status_response.json()
                    print(f"\nDocument Status:")
                    print(f"  Status: {doc_data.get('status')}")
                    print(f"  Chunks: {doc_data.get('chunk_count')}")
                    print(f"  Error: {doc_data.get('error_message')}")

                # Get document chunks
                chunks_response = await client.get(
                    f"/api/documents/{document_id}/chunks",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if chunks_response.status_code == 200:
                    chunks = chunks_response.json()
                    print(f"\nDocument has {len(chunks)} chunks")
                    if chunks:
                        print(f"First chunk preview: {chunks[0].get('content', '')[:100]}...")

            else:
                print(f"Upload failed: {response.text}")

        # Test stats endpoint (public)
        stats_response = await client.get("/api/documents/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"\nDocument Stats:")
            print(f"  Total documents: {stats.get('total_documents')}")
            print(f"  Processed: {stats.get('processed_documents')}")
            print(f"  Processing: {stats.get('processing_documents')}")
            print(f"  Errors: {stats.get('error_documents')}")

if __name__ == "__main__":
    asyncio.run(test_upload_with_jwt())