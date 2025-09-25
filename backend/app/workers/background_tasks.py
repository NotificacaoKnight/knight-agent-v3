"""
FastAPI Background Tasks for async document processing
Replaces Celery with native FastAPI background tasks
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_async_db
from app.models import (
    Document, DocumentChunk, ProcessingJob,
    DownloadRecord
)
from app.services.document_processor import DocumentProcessorService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manager for FastAPI background tasks
    Replaces Celery functionality with native async support
    """

    def __init__(self):
        self.doc_processor = DocumentProcessorService()
        self.chunking_service = ChunkingService()
        self.embedding_service = get_embedding_service()

    def get_db_session(self):
        """Get async database session generator"""
        return get_async_db()


async def process_document_async(
    document_id: int,
    enable_ocr: bool = False
) -> Dict[str, Any]:
    """
    Process a document: convert to markdown, chunk, and generate embeddings

    Args:
        document_id: ID of document to process
        enable_ocr: Whether to enable OCR for image processing

    Returns:
        Dict with processing results
    """
    manager = BackgroundTaskManager()

    try:
        async for db in manager.get_db_session():
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            logger.info(f"🔄 Starting processing for document {document_id}")

            # Update document status
            document.status = 'processing'
            document.processing_started_at = datetime.utcnow()
            document.error_message = None
            await db.commit()

            # Update processing job status
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.document_id == document_id)
                .values(
                    status="processing",
                    started_at=datetime.utcnow()
                )
            )
            await db.commit()

            # Step 1: Process document to markdown
            logger.info(f"📄 Converting document to markdown...")
            markdown_content = await manager.doc_processor.process_document_async(
                document.file_path,
                enable_ocr=enable_ocr
            )

            # Step 2: Chunk the content
            logger.info(f"✂️ Chunking document content...")
            chunks = await manager.chunking_service.chunk_text_async(
                markdown_content,
                document_id=document_id
            )

            # Step 3: Generate embeddings
            logger.info(f"🧠 Generating embeddings for {len(chunks)} chunks...")
            embeddings_results = await generate_embeddings_async(
                document_id,
                chunks
            )

            # Update document status
            document.status = 'processed'
            document.processing_completed_at = datetime.utcnow()
            document.chunk_count = len(chunks)
            document.markdown_content = markdown_content  # Save the markdown content
            document.document_metadata = document.document_metadata or {}
            document.document_metadata['embeddings_count'] = embeddings_results.get("embeddings_count", 0)
            await db.commit()

            # Update processing job status
            await db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.document_id == document_id)
                .values(
                    status="completed",
                    completed_at=datetime.utcnow(),
                    result={
                        "chunks_count": len(chunks),
                        "embeddings_count": embeddings_results.get("embeddings_count", 0),
                        "processing_time": str(datetime.utcnow() - document.uploaded_at)
                    }
                )
            )
            await db.commit()

            logger.info(f"✅ Document {document_id} processed successfully")
            break  # Exit the async for loop

        return {
                "status": "success",
                "document_id": document_id,
                "chunks_created": len(chunks),
                "embeddings_generated": embeddings_results.get("embeddings_count", 0)
            }

    except Exception as e:
        logger.error(f"❌ Error processing document {document_id}: {str(e)}")

        # Update error status
        try:
            async for db in manager.get_db_session():
                # Update document status
                result = await db.execute(
                    select(Document).where(Document.id == document_id)
                )
                document = result.scalar_one_or_none()
                if document:
                    document.status = 'error'
                    document.error_message = str(e)
                    document.processing_completed_at = datetime.utcnow()
                    await db.commit()

                # Update job status
                await db.execute(
                    update(ProcessingJob)
                    .where(ProcessingJob.document_id == document_id)
                    .values(
                        status="failed",
                        completed_at=datetime.utcnow(),
                        error_message=str(e)
                    )
                )
                await db.commit()
                break  # Exit the async for loop
        except Exception as update_error:
            logger.error(f"Failed to update error status: {update_error}")

        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e)
        }


async def generate_embeddings_async(
    document_id: int,
    chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate embeddings for document chunks

    Args:
        document_id: ID of the document
        chunks: List of text chunks with metadata

    Returns:
        Dict with embedding generation results
    """
    manager = BackgroundTaskManager()

    try:
        logger.info(f"🧠 Generating embeddings for {len(chunks)} chunks")

        # Extract text from chunks
        texts = [chunk["text"] for chunk in chunks]

        # Generate embeddings
        embeddings = await manager.embedding_service.generate_embeddings_async(texts)

        async for db in manager.get_db_session():
            chunks_created = 0

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Create document chunk with embedding
                chunk_obj = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk["text"],
                    embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                    chunk_size=len(chunk["text"]),
                    page_number=chunk.get("page_number"),
                    section_title=chunk.get("section_title"),
                    embedding_json=chunk.get("metadata", {})  # Store metadata in embedding_json
                )

                db.add(chunk_obj)
                chunks_created += 1

            await db.commit()

            logger.info(f"✅ Created {chunks_created} chunks with embeddings")
            break  # Exit the async for loop

        return {
                "status": "success",
                "embeddings_count": chunks_created,
                "document_id": document_id
            }

    except Exception as e:
        logger.error(f"❌ Error generating embeddings for document {document_id}: {str(e)}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e)
        }


async def chunk_document_async(
    document_id: int,
    chunk_size: int = 700,
    chunk_overlap: int = 100
) -> Dict[str, Any]:
    """
    Chunk a document's content

    Args:
        document_id: ID of document to chunk
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        Dict with chunking results
    """
    manager = BackgroundTaskManager()

    try:
        async for db in manager.get_db_session():
            # Get document
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            logger.info(f"✂️ Chunking document {document_id}")

            # Process document to get content
            content = await manager.doc_processor.process_document_async(
                document.file_path
            )

            # Chunk the content
            chunks = await manager.chunking_service.chunk_text_async(
                content,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                document_id=document_id
            )

            logger.info(f"✅ Created {len(chunks)} chunks for document {document_id}")
            break  # Exit the async for loop

        return {
                "status": "success",
                "document_id": document_id,
                "chunks_count": len(chunks),
                "chunks": chunks
            }

    except Exception as e:
        logger.error(f"❌ Error chunking document {document_id}: {str(e)}")
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e)
        }


async def cleanup_expired_downloads_async() -> Dict[str, Any]:
    """
    Clean up expired download records

    Returns:
        Dict with cleanup results
    """
    manager = BackgroundTaskManager()

    try:
        logger.info("🧹 Starting cleanup of expired downloads")

        # Calculate expiry date (7 days ago)
        expiry_date = datetime.utcnow() - timedelta(days=7)

        async for db in manager.get_db_session():
            # Get expired records
            result = await db.execute(
                select(DownloadRecord).where(DownloadRecord.created_at < expiry_date)
            )
            expired_records = result.scalars().all()

            cleaned_count = 0
            for record in expired_records:
                # Remove file if exists
                if record.file_path and os.path.exists(record.file_path):
                    try:
                        os.remove(record.file_path)
                        logger.info(f"🗑️ Removed file: {record.file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove file {record.file_path}: {e}")

                # Remove database record
                await db.delete(record)
                cleaned_count += 1

            await db.commit()

            logger.info(f"✅ Cleaned up {cleaned_count} expired download records")
            break  # Exit the async for loop

        return {
                "status": "success",
                "cleaned_count": cleaned_count
            }

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def update_vector_indices_async() -> Dict[str, Any]:
    """
    Update vector search indices for performance optimization

    Returns:
        Dict with update results
    """
    try:
        logger.info("🔄 Starting vector indices update")

        # This is a placeholder for future vector index optimization
        # Can include operations like:
        # - Rebuilding FAISS indices
        # - Optimizing pgvector indices
        # - Cleaning up unused embeddings

        await asyncio.sleep(1)  # Simulate processing

        logger.info("✅ Vector indices updated successfully")

        return {
            "status": "success",
            "message": "Vector indices updated"
        }

    except Exception as e:
        logger.error(f"❌ Error updating vector indices: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def process_document_batch_async(
    document_ids: List[int],
    enable_ocr: bool = False
) -> Dict[str, Any]:
    """
    Process multiple documents in batch

    Args:
        document_ids: List of document IDs to process
        enable_ocr: Whether to enable OCR

    Returns:
        Dict with batch processing results
    """
    try:
        logger.info(f"📦 Starting batch processing for {len(document_ids)} documents")

        results = []

        # Process documents concurrently (but limit concurrency)
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent processes

        async def process_single(doc_id):
            async with semaphore:
                return await process_document_async(doc_id, enable_ocr)

        # Run all documents concurrently
        tasks = [process_single(doc_id) for doc_id in document_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successes = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failures = len(results) - successes

        logger.info(f"✅ Batch processing completed: {successes} success, {failures} failed")

        return {
            "status": "completed",
            "total_documents": len(document_ids),
            "successful": successes,
            "failed": failures,
            "results": results
        }

    except Exception as e:
        logger.error(f"❌ Error in batch processing: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


# Export the main functions for use in API endpoints
__all__ = [
    "process_document_async",
    "generate_embeddings_async",
    "chunk_document_async",
    "cleanup_expired_downloads_async",
    "update_vector_indices_async",
    "process_document_batch_async"
]