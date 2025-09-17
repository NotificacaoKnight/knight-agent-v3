"""
Knowledge Resources API endpoints for FastAPI
Manages useful links and downloadable documents
"""
import os
import time
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
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

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


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
            color=category.color,
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
            color=new_category.color,
            link_count=0,
            document_count=0,
            is_active=new_category.is_active,
            created_at=new_category.created_at,
            updated_at=new_category.updated_at
        )

    except Exception as e:
        logger.error(f"Create category error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=List[ResourceCategoryResponse])
async def list_categories(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
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
                color=cat.color,
                link_count=link_count,
                document_count=doc_count,
                is_active=cat.is_active,
                created_at=cat.created_at,
                updated_at=cat.updated_at
            ))

        return category_list

    except Exception as e:
        logger.error(f"List categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Useful Links endpoints
@router.post("/links", response_model=UsefulLinkResponse)
async def create_link(
    link: UsefulLinkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new useful link"""
    try:
        new_link = UsefulLink(
            title=link.title,
            url=str(link.url),
            description=link.description,
            category_id=link.category_id,
            ai_guidance=link.ai_guidance,
            tags=link.tags or [],
            is_active=link.is_active,
            created_by=current_user.id
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
            category_id=new_link.category_id,
            category_name=category_name,
            ai_guidance=new_link.ai_guidance,
            tags=new_link.tags,
            send_count=new_link.send_count,
            click_count=new_link.click_count,
            is_active=new_link.is_active,
            created_by=new_link.created_by,
            created_at=new_link.created_at,
            updated_at=new_link.updated_at
        )

    except Exception as e:
        logger.error(f"Create link error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/links", response_model=List[UsefulLinkResponse])
async def list_links(
    category_id: Optional[int] = None,
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db)
):
    """List useful links"""
    try:
        query = select(UsefulLink)

        if active_only:
            query = query.where(UsefulLink.is_active == True)

        if category_id:
            query = query.where(UsefulLink.category_id == category_id)

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
                category_id=link.category_id,
                category_name=category_name,
                ai_guidance=link.ai_guidance,
                tags=link.tags,
                send_count=link.send_count,
                click_count=link.click_count,
                is_active=link.is_active,
                created_by=link.created_by,
                created_at=link.created_at,
                updated_at=link.updated_at
            ))

        return link_list

    except Exception as e:
        logger.error(f"List links error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Downloadable Documents endpoints
@router.post("/documents", response_model=DownloadableDocumentResponse)
async def create_document(
    document: DownloadableDocumentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new downloadable document"""
    try:
        # Validate file exists
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # Get file info
        file_stat = os.stat(document.file_path)
        file_name = os.path.basename(document.file_path)

        new_doc = DownloadableDocument(
            title=document.title,
            file_path=document.file_path,
            file_name=file_name,
            file_size=file_stat.st_size,
            description=document.description,
            category_id=document.category_id,
            ai_guidance=document.ai_guidance,
            tags=document.tags or [],
            is_active=document.is_active,
            created_by=current_user.id
        )

        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        # Get category name
        category_name = None
        if new_doc.category_id:
            cat_result = await db.execute(
                select(ResourceCategory).where(ResourceCategory.id == new_doc.category_id)
            )
            category = cat_result.scalar_one_or_none()
            if category:
                category_name = category.name

        return DownloadableDocumentResponse(
            id=new_doc.id,
            title=new_doc.title,
            file_path=new_doc.file_path,
            file_name=new_doc.file_name,
            file_size=new_doc.file_size,
            description=new_doc.description,
            category_id=new_doc.category_id,
            category_name=category_name,
            ai_guidance=new_doc.ai_guidance,
            tags=new_doc.tags,
            download_count=new_doc.download_count,
            send_count=new_doc.send_count,
            is_active=new_doc.is_active,
            created_by=new_doc.created_by,
            created_at=new_doc.created_at,
            updated_at=new_doc.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=List[DownloadableDocumentResponse])
async def list_documents(
    category_id: Optional[int] = None,
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db)
):
    """List downloadable documents"""
    try:
        query = select(DownloadableDocument)

        if active_only:
            query = query.where(DownloadableDocument.is_active == True)

        if category_id:
            query = query.where(DownloadableDocument.category_id == category_id)

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
                file_path=doc.file_path,
                file_name=doc.file_name,
                file_size=doc.file_size,
                description=doc.description,
                category_id=doc.category_id,
                category_name=category_name,
                ai_guidance=doc.ai_guidance,
                tags=doc.tags,
                download_count=doc.download_count,
                send_count=doc.send_count,
                is_active=doc.is_active,
                created_by=doc.created_by,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            ))

        return doc_list

    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/download")
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

        if not os.path.exists(document.file_path):
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
            path=document.file_path,
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
                    category_id=link.category_id,
                    category_name=None,  # TODO: Get category name
                    ai_guidance=link.ai_guidance,
                    tags=link.tags,
                    send_count=link.send_count,
                    click_count=link.click_count,
                    is_active=link.is_active,
                    created_by=link.created_by,
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
                    file_path=doc.file_path,
                    file_name=doc.file_name,
                    file_size=doc.file_size,
                    description=doc.description,
                    category_id=doc.category_id,
                    category_name=None,  # TODO: Get category name
                    ai_guidance=doc.ai_guidance,
                    tags=doc.tags,
                    download_count=doc.download_count,
                    send_count=doc.send_count,
                    is_active=doc.is_active,
                    created_by=doc.created_by,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at
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

            # Increment click count
            link.click_count += 1

            await db.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Track click error: {e}")
        return {"success": False}