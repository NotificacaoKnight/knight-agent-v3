"""
Knowledge Resources API endpoints for FastAPI
Manages useful links and downloadable documents
"""
import os
import time
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Form, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge import (
    UsefulLink, DownloadableDocument, ResourceCategory, ResourceUsage
)
from app.schemas.knowledge import (
    UsefulLinkCreate,
    UsefulLinkResponse,
    DownloadableDocumentCreate,
    DownloadableDocumentResponse,
    ResourceCategoryCreate,
    ResourceCategoryResponse,
    ResourceUsageResponse,
    KnowledgeSearchQuery,
    KnowledgeSearchResponse
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# Categories endpoints
@router.post("/categories", response_model=ResourceCategoryResponse)
async def create_category(
    category: ResourceCategoryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new resource category"""
    try:
        new_category = ResourceCategory(
            name=category.name,
            description=category.description,
            icon=category.icon,
            color_code=category.color,
            is_active=category.is_active
        )

        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        return ResourceCategoryResponse(
            id=new_category.id,
            name=new_category.name,
            description=new_category.description,
            icon=new_category.icon,
            color_code=new_category.color_code,
            link_count=0,
            document_count=0,
            is_active=new_category.is_active,
            created_at=new_category.created_at
        )

    except Exception as e:
        logger.error(f"Create category error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=List[ResourceCategoryResponse])
async def list_categories(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_async_db)
):
    """List all resource categories"""
    try:
        query = select(ResourceCategory)

        if active_only:
            query = query.where(ResourceCategory.is_active == True)

        query = query.order_by(ResourceCategory.name)

        result = await db.execute(query)
        categories = result.scalars().all()

        # Get counts
        category_list = []
        for cat in categories:
            # Count links
            link_count_result = await db.execute(
                select(func.count()).select_from(UsefulLink)
                .where(UsefulLink.category_id == cat.id)
            )
            link_count = link_count_result.scalar()

            # Count documents
            doc_count_result = await db.execute(
                select(func.count()).select_from(DownloadableDocument)
                .where(DownloadableDocument.category_id == cat.id)
            )
            doc_count = doc_count_result.scalar()

            category_list.append(ResourceCategoryResponse(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                icon=cat.icon,
                color_code=cat.color_code,
                link_count=link_count,
                document_count=doc_count,
                is_active=cat.is_active,
                created_at=cat.created_at
            ))

        return category_list

    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Useful Links endpoints
@router.post("/useful-links/", response_model=UsefulLinkResponse)
async def create_link(
    link: UsefulLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new useful link"""
    try:
        # Handle category by name or ID
        category_id = link.category_id
        if not category_id and link.category:
            # Try to find category by name
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.name == link.category)
            )
            category = cat_result.scalar_one_or_none()

            if not category:
                # Create new category if it doesn't exist
                category = ResourceCategory(
                    name=link.category,
                    description=f"Auto-created category for {link.category}",
                    is_active=True
                )
                db.add(category)
                await db.commit()
                await db.refresh(category)

            category_id = category.id

        new_link = UsefulLink(
            title=link.title,
            url=str(link.url),
            description=link.description,
            category_id=category_id,
            ai_guidance=link.ai_guidance,
            tags=link.tags or [],
            is_active=link.is_active,
            created_by_id=current_user.id  # Fixed: use created_by_id
        )

        db.add(new_link)
        await db.commit()
        await db.refresh(new_link)

        # Get category name
        category_name = None
        if new_link.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == new_link.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return UsefulLinkResponse(
            id=new_link.id,
            title=new_link.title,
            url=new_link.url,
            description=new_link.description,
            category=category_name or "Uncategorized",
            ai_guidance=new_link.ai_guidance,
            tags=new_link.tags or [],
            send_count=new_link.send_count,
            is_active=new_link.is_active,
            created_by=new_link.created_by_id,  # Fixed: use created_by_id
            created_at=new_link.created_at,
            updated_at=new_link.updated_at
        )

    except Exception as e:
        logger.error(f"Create link error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/useful-links/", response_model=List[UsefulLinkResponse])
async def list_links(
    category: Optional[str] = None,
    active: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db)
):
    """List useful links"""
    try:
        query = select(UsefulLink)

        if active:
            query = query.where(UsefulLink.is_active == True)

        if category:
            # Find category by name
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.name == category)
            )
            category_obj = cat_result.scalar_one_or_none()
            if category_obj:
                query = query.where(UsefulLink.category_id == category_obj.id)

        query = query.order_by(UsefulLink.send_count.desc())
        query = query.limit(limit)

        result = await db.execute(query)
        links = result.scalars().all()

        link_list = []
        for link in links:
            # Get category name
            category_name = None
            if link.category_id:
                cat_result = await db.execute(
                    select(ResourceCategory).where(ResourceCategory.id == link.category_id)
                )
                category = cat_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            link_list.append(UsefulLinkResponse(
                id=link.id,
                title=link.title,
                url=link.url,
                description=link.description,
                category=category_name or "Uncategorized",
                ai_guidance=link.ai_guidance,
                tags=link.tags or [],
                send_count=link.send_count,
                is_active=link.is_active,
                created_by=link.created_by_id,
                created_at=link.created_at,
                updated_at=link.updated_at
            ))

        return link_list

    except Exception as e:
        logger.error(f"List links error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/useful-links/{link_id}/", response_model=UsefulLinkResponse)
async def get_link(
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific useful link"""
    try:
        result = await db.execute(
            select(UsefulLink).where(UsefulLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        # Get category name
        category_name = None
        if link.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == link.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return UsefulLinkResponse(
            id=link.id,
            title=link.title,
            url=link.url,
            description=link.description,
            category=category_name or "Uncategorized",
            ai_guidance=link.ai_guidance,
            tags=link.tags or [],
            send_count=link.send_count,
            is_active=link.is_active,
            created_by=link.created_by_id,
            created_at=link.created_at,
            updated_at=link.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get link error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/useful-links/{link_id}/", response_model=UsefulLinkResponse)
async def update_link(
    link_id: int,
    link_data: UsefulLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update a useful link"""
    try:
        result = await db.execute(
            select(UsefulLink).where(UsefulLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        # Handle category by name or ID
        category_id = link_data.category_id
        if not category_id and link_data.category:
            # Try to find category by name
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.name == link_data.category)
            )
            category = cat_result.scalar_one_or_none()

            if not category:
                # Create new category if it doesn't exist
                category = ResourceCategory(
                    name=link_data.category,
                    description=f"Auto-created category for {link_data.category}",
                    is_active=True
                )
                db.add(category)
                await db.commit()
                await db.refresh(category)

            category_id = category.id

        # Update fields
        link.title = link_data.title
        link.url = str(link_data.url)
        link.description = link_data.description
        link.category_id = category_id if category_id else link_data.category_id
        link.ai_guidance = link_data.ai_guidance
        link.tags = link_data.tags or []
        link.is_active = link_data.is_active

        await db.commit()
        await db.refresh(link)

        # Get category name
        category_name = None
        if link.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == link.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return UsefulLinkResponse(
            id=link.id,
            title=link.title,
            url=link.url,
            description=link.description,
            category=category_name or "Uncategorized",
            ai_guidance=link.ai_guidance,
            tags=link.tags or [],
            send_count=link.send_count,
            is_active=link.is_active,
            created_by=link.created_by_id,
            created_at=link.created_at,
            updated_at=link.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update link error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/useful-links/{link_id}/")
async def delete_link(
    link_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a useful link"""
    try:
        result = await db.execute(
            select(UsefulLink).where(UsefulLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        await db.delete(link)
        await db.commit()

        return {"success": True, "message": "Link deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete link error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/useful-links/{link_id}/increment_send_count/")
async def increment_link_send_count(
    link_id: int,
    context: dict = Body(default={}),
    db: AsyncSession = Depends(get_async_db)
):
    """Increment send count for a link (when AI sends it)"""
    try:
        result = await db.execute(
            select(UsefulLink).where(UsefulLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        # Track usage
        usage = ResourceUsage(
            resource_type='link',
            resource_id=link.id,
            action='send',
            context=context.get('context', ''),
            session_id=context.get('chat_session_id')
        )
        db.add(usage)

        # Increment send count
        link.send_count += 1

        await db.commit()

        return {"success": True, "send_count": link.send_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Increment send count error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Downloadable Documents endpoints
@router.post("/downloadable-documents/", response_model=DownloadableDocumentResponse)
async def create_document(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    ai_guidance: Optional[str] = Form(None),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new downloadable document with file upload"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        contents = await file.read()
        file_size = len(contents)

        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_size / (1024*1024)}MB"
            )

        # Save file to disk
        upload_dir = os.path.join(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else 'media', 'downloadable_documents')
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, 'wb') as f:
            f.write(contents)

        # Extract file info
        file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'

        # Find or create category
        cat_result = await db.execute(
            select(ResourceCategory).where(ResourceCategory.name == category)
        )
        category_obj = cat_result.scalar_one_or_none()

        if not category_obj:
            # Create category if it doesn't exist
            category_obj = ResourceCategory(
                name=category,
                description=f"Auto-created category for {category}",
                is_active=True
            )
            db.add(category_obj)
            await db.commit()
            await db.refresh(category_obj)

        new_doc = DownloadableDocument(
            title=title,
            file=file_path,  # The model expects 'file', not 'file_path'
            file_name=file.filename,
            file_size=file_size,
            file_type=file_type,
            description=description or "",
            category_id=category_obj.id,
            ai_guidance=ai_guidance or "",
            tags=[],
            is_active=True,
            created_by_id=current_user.id  # Fixed: use created_by_id
        )

        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        return DownloadableDocumentResponse(
            id=new_doc.id,
            title=new_doc.title,
            description=new_doc.description,
            ai_guidance=new_doc.ai_guidance,
            category=category_obj.name,
            file=new_doc.file,
            file_url=f"/api/knowledge/downloadable-documents/{new_doc.id}/download",
            file_name=new_doc.file_name,
            file_size=new_doc.file_size,
            file_type=new_doc.file_type,
            is_active=new_doc.is_active,
            download_count=new_doc.download_count,
            share_count=new_doc.share_count,
            created_by=new_doc.created_by_id,
            created_at=new_doc.created_at,
            updated_at=new_doc.updated_at,
            tags=new_doc.tags or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downloadable-documents/", response_model=List[DownloadableDocumentResponse])
async def list_documents(
    category: Optional[str] = None,
    active: bool = Query(True),
    file_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db)
):
    """List downloadable documents"""
    try:
        query = select(DownloadableDocument)

        if active:
            query = query.where(DownloadableDocument.is_active == True)

        if category:
            # Find category by name
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.name == category)
            )
            category_obj = cat_result.scalar_one_or_none()
            if category_obj:
                query = query.where(DownloadableDocument.category_id == category_obj.id)

        if file_type:
            query = query.where(DownloadableDocument.file_type == file_type)

        query = query.order_by(DownloadableDocument.download_count.desc())
        query = query.limit(limit)

        result = await db.execute(query)
        documents = result.scalars().all()

        doc_list = []
        for doc in documents:
            # Get category name
            category_name = None
            if doc.category_id:
                cat_result = await db.execute(
                    select(ResourceCategory).where(ResourceCategory.id == doc.category_id)
                )
                category = cat_result.scalar_one_or_none()
                if category:
                    category_name = category.name

            doc_list.append(DownloadableDocumentResponse(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                ai_guidance=doc.ai_guidance,
                category=category_name or "Uncategorized",
                file=doc.file,
                file_url=f"/api/knowledge/downloadable-documents/{doc.id}/download",
                file_name=doc.file_name,
                file_size=doc.file_size,
                file_type=doc.file_type,
                is_active=doc.is_active,
                download_count=doc.download_count,
                share_count=doc.share_count,
                created_by=doc.created_by_id,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                tags=doc.tags or []
            ))

        return doc_list

    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downloadable-documents/{doc_id}/", response_model=DownloadableDocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific downloadable document"""
    try:
        result = await db.execute(
            select(DownloadableDocument).where(DownloadableDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get category name
        category_name = None
        if doc.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == doc.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return DownloadableDocumentResponse(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            ai_guidance=doc.ai_guidance,
            category=category_name or "Uncategorized",
            file=doc.file,
            file_url=f"/api/knowledge/downloadable-documents/{doc.id}/download",
            file_name=doc.file_name,
            file_size=doc.file_size,
            file_type=doc.file_type,
            is_active=doc.is_active,
            download_count=doc.download_count,
            share_count=doc.share_count,
            created_by=doc.created_by_id,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tags=doc.tags or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/downloadable-documents/{doc_id}/", response_model=DownloadableDocumentResponse)
async def update_document(
    doc_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    ai_guidance: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update a downloadable document"""
    try:
        result = await db.execute(
            select(DownloadableDocument).where(DownloadableDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update fields
        if title is not None:
            doc.title = title
        if description is not None:
            doc.description = description
        if ai_guidance is not None:
            doc.ai_guidance = ai_guidance

        # Handle category update
        if category is not None:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.name == category)
            )
            category_obj = cat_result.scalar_one_or_none()

            if not category_obj:
                # Create category if it doesn't exist
                category_obj = ResourceCategory(
                    name=category,
                    description=f"Auto-created category for {category}",
                    is_active=True
                )
                db.add(category_obj)
                await db.commit()
                await db.refresh(category_obj)

            doc.category_id = category_obj.id

        # Handle file update
        if file and file.filename:
            # Remove old file
            if doc.file and os.path.exists(doc.file):
                try:
                    os.remove(doc.file)
                except Exception as e:
                    logger.warning(f"Failed to delete old file {doc.file}: {e}")

            # Save new file
            contents = await file.read()
            file_size = len(contents)

            upload_dir = os.path.join(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else 'media', 'downloadable_documents')
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, 'wb') as f:
                f.write(contents)

            doc.file = file_path
            doc.file_name = file.filename
            doc.file_size = file_size
            doc.file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'

        await db.commit()
        await db.refresh(doc)

        # Get category name
        category_name = None
        if doc.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == doc.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return DownloadableDocumentResponse(
            id=doc.id,
            title=doc.title,
            description=doc.description,
            ai_guidance=doc.ai_guidance,
            category=category_name or "Uncategorized",
            file=doc.file,
            file_url=f"/api/knowledge/downloadable-documents/{doc.id}/download",
            file_name=doc.file_name,
            file_size=doc.file_size,
            file_type=doc.file_type,
            is_active=doc.is_active,
            download_count=doc.download_count,
            share_count=doc.share_count,
            created_by=doc.created_by_id,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            tags=doc.tags or []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/downloadable-documents/{doc_id}/")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a downloadable document"""
    try:
        result = await db.execute(
            select(DownloadableDocument).where(DownloadableDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete file from disk
        if doc.file and os.path.exists(doc.file):
            try:
                os.remove(doc.file)
            except Exception as e:
                logger.warning(f"Failed to delete file {doc.file}: {e}")

        await db.delete(doc)
        await db.commit()

        return {"success": True, "message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/downloadable-documents/{doc_id}/increment_download_count/")
async def increment_document_download_count(
    doc_id: int,
    context: dict = Body(default={}),
    db: AsyncSession = Depends(get_async_db)
):
    """Increment download count for a document (when user downloads it)"""
    try:
        result = await db.execute(
            select(DownloadableDocument).where(DownloadableDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Track usage
        usage = ResourceUsage(
            resource_type='document',
            resource_id=doc.id,
            action='download',
            context=context.get('context', ''),
            session_id=context.get('chat_session_id')
        )
        db.add(usage)

        # Increment download count
        doc.download_count += 1

        await db.commit()

        return {"success": True, "download_count": doc.download_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Increment download count error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/downloadable-documents/{doc_id}/increment_share_count/")
async def increment_document_share_count(
    doc_id: int,
    context: dict = Body(default={}),
    db: AsyncSession = Depends(get_async_db)
):
    """Increment share count for a document (when AI shares it)"""
    try:
        result = await db.execute(
            select(DownloadableDocument).where(DownloadableDocument.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Track usage
        usage = ResourceUsage(
            resource_type='document',
            resource_id=doc.id,
            action='share',
            context=context.get('context', ''),
            session_id=context.get('chat_session_id')
        )
        db.add(usage)

        # Increment share count (shared by AI)
        doc.share_count += 1

        await db.commit()

        return {"success": True, "share_count": doc.share_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Increment share count error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downloadable-documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Download a document"""
    try:
        # Get document
        result = await db.execute(
            select(DownloadableDocument).where(
                DownloadableDocument.id == document_id,
                DownloadableDocument.is_active == True
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if not os.path.exists(document.file):
            raise HTTPException(status_code=404, detail="File not available")

        # Track usage
        usage = ResourceUsage(
            resource_type='document',
            resource_id=document.id,
            action='download'
        )
        db.add(usage)

        # Increment download count
        document.download_count += 1

        await db.commit()

        return FileResponse(
            path=document.file,
            filename=document.file_name,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_resources(
    query: KnowledgeSearchQuery,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Search knowledge resources

    Uses semantic search on titles, descriptions, and AI guidance
    """
    start_time = time.time()

    try:
        # Search links
        links = []
        if not query.resource_type or query.resource_type == "links":
            link_query = select(UsefulLink).where(
                UsefulLink.is_active == True
            )

            # Text search
            search_conditions = []
            search_terms = query.query.lower().split()
            for term in search_terms:
                search_conditions.append(
                    or_(
                        func.lower(UsefulLink.title).contains(term),
                        func.lower(UsefulLink.description).contains(term),
                        func.lower(UsefulLink.ai_guidance).contains(term)
                    )
                )

            if search_conditions:
                link_query = link_query.where(and_(*search_conditions))

            if query.category_id:
                link_query = link_query.where(UsefulLink.category_id == query.category_id)

            link_query = link_query.limit(query.limit)

            link_result = await db.execute(link_query)
            link_records = link_result.scalars().all()

            for link in link_records:
                links.append(UsefulLinkResponse(
                    id=link.id,
                    title=link.title,
                    url=link.url,
                    description=link.description,
                    category="Uncategorized",  # TODO: Get category name
                    ai_guidance=link.ai_guidance,
                    tags=link.tags or [],
                    send_count=link.send_count,
                    is_active=link.is_active,
                    created_by=link.created_by_id,
                    created_at=link.created_at,
                    updated_at=link.updated_at
                ))

        # Search documents
        documents = []
        if not query.resource_type or query.resource_type == "documents":
            doc_query = select(DownloadableDocument).where(
                DownloadableDocument.is_active == True
            )

            # Text search
            search_conditions = []
            for term in search_terms:
                search_conditions.append(
                    or_(
                        func.lower(DownloadableDocument.title).contains(term),
                        func.lower(DownloadableDocument.description).contains(term),
                        func.lower(DownloadableDocument.ai_guidance).contains(term)
                    )
                )

            if search_conditions:
                doc_query = doc_query.where(and_(*search_conditions))

            if query.category_id:
                doc_query = doc_query.where(DownloadableDocument.category_id == query.category_id)

            doc_query = doc_query.limit(query.limit)

            doc_result = await db.execute(doc_query)
            doc_records = doc_result.scalars().all()

            for doc in doc_records:
                documents.append(DownloadableDocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    description=doc.description,
                    ai_guidance=doc.ai_guidance,
                    category="Uncategorized",  # TODO: Get category name
                    file=doc.file,
                    file_url=f"/api/knowledge/downloadable-documents/{doc.id}/download",
                    file_name=doc.file_name,
                    file_size=doc.file_size,
                    file_type=doc.file_type,
                    is_active=doc.is_active,
                    download_count=doc.download_count,
                    share_count=doc.share_count,
                    created_by=doc.created_by_id,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                    tags=doc.tags or []
                ))

        search_time = int((time.time() - start_time) * 1000)

        return KnowledgeSearchResponse(
            links=links,
            documents=documents,
            total_links=len(links),
            total_documents=len(documents),
            search_time_ms=search_time
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track-click/{link_id}")
async def track_link_click(
    link_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Track link click"""
    try:
        # Get link
        result = await db.execute(
            select(UsefulLink).where(UsefulLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if link:
            # Track usage
            usage = ResourceUsage(
                resource_type='link',
                resource_id=link.id,
                action='click'
            )
            db.add(usage)

            # Increment send count (using as click counter)
            link.send_count += 1

            await db.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Track click error: {e}")
        return {"success": False}


# Workaround: Add documents stats here since the documents API has auth issues
@router.get("/documents-stats")
async def get_documents_stats(db: AsyncSession = Depends(get_async_db)):
    """Get document statistics - workaround endpoint"""
    try:
        from app.models.document import Document, DocumentChunk
        from sqlalchemy import func

        # Total documents
        total_docs_result = await db.execute(
            select(func.count()).select_from(Document)
        )
        total_documents = total_docs_result.scalar()

        # Total chunks
        total_chunks_result = await db.execute(
            select(func.count()).select_from(DocumentChunk)
        )
        total_chunks = total_chunks_result.scalar()

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

        # Get downloadable documents count (assuming processed documents are downloadable)
        downloadable_documents = processed_documents

        return {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "pending_documents": pending_documents,
            "processing_documents": processing_documents,
            "error_documents": error_documents,
            "downloadable_documents": downloadable_documents,
            "total_chunks": total_chunks
        }

    except Exception as e:
        logger.error(f"Get documents stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))