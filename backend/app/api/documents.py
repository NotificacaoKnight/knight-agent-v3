"""
Document management API endpoints for FastAPI
"""
import os
import logging
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentChunk, ProcessingJob
from app.schemas.document import (
    DocumentUpload,
    DocumentResponse,
    DocumentListResponse,
    ChunkResponse,
    ProcessingJobResponse,
    DocumentStatsResponse,
    DeleteDocumentResponse,
    DocumentContentResponse
)
from app.core.config import settings
from app.workers.background_tasks import process_document_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    enable_ocr: bool = Form(False),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    language: str = Form("pt"),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document for processing

    - **file**: Document file (PDF, DOCX, TXT, etc.)
    - **title**: Document title
    - **enable_ocr**: Enable OCR for scanned documents
    - **chunk_size**: Custom chunk size (default from settings)
    - **chunk_overlap**: Custom chunk overlap (default from settings)
    - **language**: Document language (pt, en)
    - **tags**: Comma-separated tags
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = 0
        contents = await file.read()
        file_size = len(contents)

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_size / (1024*1024)}MB"
            )

        # Save file to disk
        upload_dir = os.path.join(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else 'media', 'documents')
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, 'wb') as f:
            f.write(contents)

        # Extract file info
        file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'

        # Calculate checksum
        import hashlib
        checksum = hashlib.sha256(contents).hexdigest()

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Create document record
        document = Document(
            uploaded_by_id=current_user.id,
            title=title,
            original_filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            checksum=checksum,
            status='uploaded',
            document_metadata={
                'language': language,
                'enable_ocr': enable_ocr,
                'chunk_size': chunk_size or settings.CHUNK_SIZE if hasattr(settings, 'CHUNK_SIZE') else 700,
                'chunk_overlap': chunk_overlap or settings.CHUNK_OVERLAP if hasattr(settings, 'CHUNK_OVERLAP') else 100,
                'tags': tag_list
            }
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Create processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='full_processing',
            status='pending'
        )
        db.add(job)
        await db.commit()

        # Schedule background processing
        background_tasks.add_task(
            process_document_async,
            document.id,
            enable_ocr
        )

        logger.info(f"Document uploaded: {document.id} - {document.title}")

        return DocumentResponse(
            id=document.id,
            title=document.title,
            filename=document.original_filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
            processing_started_at=document.processing_started_at,
            processing_completed_at=document.processing_completed_at,
            error_message=document.error_message,
            document_metadata=document.document_metadata,
            tags=tag_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_document_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """Get document statistics - public endpoint"""
    try:
        # Total documents
        total_docs_result = await db.execute(
            select(func.count()).select_from(Document)
        )
        total_documents = total_docs_result.scalar() or 0

        # Total chunks
        total_chunks_result = await db.execute(
            select(func.count()).select_from(DocumentChunk)
        )
        total_chunks = total_chunks_result.scalar() or 0

        # Documents by status
        status_result = await db.execute(
            select(Document.status, func.count())
            .group_by(Document.status)
        )
        documents_by_status = dict(status_result.all())

        # Get individual status counts
        processed_documents = documents_by_status.get('processed', 0)
        pending_documents = documents_by_status.get('pending', 0) + documents_by_status.get('uploaded', 0)
        processing_documents = documents_by_status.get('processing', 0)
        error_documents = documents_by_status.get('error', 0)

        # Get downloadable documents count
        downloadable_result = await db.execute(
            select(func.count()).select_from(Document)
            .where(Document.is_downloadable == True)
        )
        downloadable_documents = downloadable_result.scalar() or 0

        return DocumentStatsResponse(
            total_documents=total_documents,
            processed_documents=processed_documents,
            pending_documents=pending_documents,
            processing_documents=processing_documents,
            error_documents=error_documents,
            downloadable_documents=downloadable_documents,
            total_chunks=total_chunks
        )

    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    List user's documents with pagination

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status
    - **search**: Search in title
    """
    try:
        # Build query - Admins veem todos os documentos
        query = select(Document).options(selectinload(Document.uploaded_by))

        if status:
            query = query.where(Document.status == status)

        if search:
            query = query.where(Document.title.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(Document.uploaded_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute query with user relationship
        result = await db.execute(query)
        documents = result.scalars().all()

        # Format response
        document_list = []
        for doc in documents:
            # Get user information if available
            uploaded_by_name = None
            uploaded_by_email = None

            if doc.uploaded_by:
                uploaded_by_name = doc.uploaded_by.display_name or doc.uploaded_by.username
                uploaded_by_email = doc.uploaded_by.email

            document_list.append(DocumentResponse(
                id=doc.id,
                title=doc.title,
                filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                status=doc.status,
                page_count=doc.document_metadata.get('page_count', 0) if doc.document_metadata else 0,
                chunk_count=doc.chunk_count,
                created_at=doc.uploaded_at,
                updated_at=doc.updated_at,
                processing_started_at=doc.processing_started_at,
                processing_completed_at=doc.processing_completed_at,
                error_message=doc.error_message,
                document_metadata=doc.document_metadata,
                tags=doc.document_metadata.get('tags', []) if doc.document_metadata else [],
                access_count=doc.access_count or 0,
                uploaded_by_name=uploaded_by_name,
                uploaded_by_email=uploaded_by_email
            ))

        # Calculate pages for pagination
        pages = (total + page_size - 1) // page_size

        return DocumentListResponse(
            documents=document_list,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )

    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get document details"""
    try:
        # Get document
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.uploaded_by_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentResponse(
            id=document.id,
            title=document.title,
            filename=document.original_filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
            processing_started_at=document.processing_started_at,
            processing_completed_at=document.processing_completed_at,
            error_message=document.error_message,
            document_metadata=document.document_metadata,
            tags=document.document_metadata.get('tags', []) if document.document_metadata else [],
            access_count=document.access_count or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get document chunks"""
    try:
        # Verify document ownership
        doc_result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.uploaded_by_id == current_user.id
            )
        )
        document = doc_result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get chunks
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(limit)
        )
        chunks = result.scalars().all()

        # Format response
        chunk_list = []
        for chunk in chunks:
            chunk_list.append(ChunkResponse(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                has_embedding=chunk.embedding is not None,
                chunk_metadata=chunk.chunk_metadata
            ))

        return chunk_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chunks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
async def get_document_content(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get document content (processed markdown)"""
    try:
        # Get document by ID (no ownership verification for admin interface)
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Use markdown_content if available, otherwise reconstruct from chunks
        content = document.markdown_content or ""

        if not content:
            # Fallback: reconstruct content from chunks
            chunks_result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = chunks_result.scalars().all()

            # Reconstruct content from chunks
            content_parts = []
            for chunk in chunks:
                if chunk.content:
                    content_parts.append(chunk.content.strip())

            content = "\n\n".join(content_parts)

        # Count chunks
        chunks_count_result = await db.execute(
            select(func.count()).select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        chunks_count = chunks_count_result.scalar() or 0

        return DocumentContentResponse(
            title=document.title,
            content=content,
            metadata=document.document_metadata,
            chunks_count=chunks_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get content error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document and all associated data"""
    try:
        # Get document by ID (no ownership verification for admin interface)
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Count chunks to be deleted
        chunk_count_result = await db.execute(
            select(func.count()).select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        chunk_count = chunk_count_result.scalar()

        # Delete chunks
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # Delete processing jobs
        await db.execute(
            delete(ProcessingJob).where(ProcessingJob.document_id == document_id)
        )

        # Delete files from disk - complete cleanup
        files_deleted = []

        # 1. Remove original file
        if document.file_path and os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
                files_deleted.append(f"Original: {document.file_path}")
                logger.info(f"Original file removed: {document.file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete original file {document.file_path}: {e}")

        # 2. Remove processed directory and files
        processed_paths_to_try = [
            document.processed_path,
            f"/home/felipealbertuxd/knight-agent/backend/processed_documents/{document_id}/",
            f"processed_documents/{document_id}/"
        ]

        for processed_path in processed_paths_to_try:
            if not processed_path:
                continue

            try:
                # If it's a file, get parent directory
                if processed_path.endswith('.md'):
                    processed_dir = os.path.dirname(processed_path)
                else:
                    processed_dir = processed_path

                if os.path.exists(processed_dir):
                    shutil.rmtree(processed_dir)
                    files_deleted.append(f"Processed: {processed_dir}")
                    logger.info(f"Processed directory removed: {processed_dir}")
                    break

            except Exception as e:
                logger.warning(f"Failed to remove processed directory {processed_path}: {e}")

        # Delete document record
        await db.delete(document)
        await db.commit()

        logger.info(f"Document deleted: {document_id}")

        return DeleteDocumentResponse(
            success=True,
            message="Document deleted successfully",
            document_id=document_id,
            chunks_deleted=chunk_count,
            files_deleted=files_deleted
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Download original document file"""
    try:
        # Get document by ID (no ownership verification for admin interface)
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if not document.file_path or not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=document.file_path,
            filename=document.original_filename,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    enable_ocr: bool = False,
    db: AsyncSession = Depends(get_async_db)
):
    """Reprocess a document"""
    try:
        # Get document by ID (no ownership verification for admin interface)
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update status
        document.status = 'processing'
        document.error_message = None

        # Create new processing job
        job = ProcessingJob(
            document_id=document.id,
            job_type='reprocessing',
            status='pending'
        )
        db.add(job)
        await db.commit()

        # Schedule background processing
        background_tasks.add_task(
            process_document_async,
            document.id,
            enable_ocr
        )

        return {"message": "Document reprocessing started", "job_id": job.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reprocess error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


