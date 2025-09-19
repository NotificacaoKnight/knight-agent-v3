"""
File downloads API endpoints for FastAPI
Temporary file distribution with 7-day expiry
"""
import os
import uuid
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.downloads import DownloadRecord, DownloadSession
from app.schemas.downloads import (
    DownloadRequestCreate,
    DownloadRecordResponse,
    DownloadSessionResponse,
    DownloadStatsResponse
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.post("/create", response_model=DownloadRecordResponse)
async def create_download_link(
    download_request: DownloadRequestCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a temporary download link

    File will be available for download for the specified number of days (max 30)
    """
    try:
        # Validate file exists
        if not os.path.exists(download_request.file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # Get file info
        file_stat = os.stat(download_request.file_path)
        file_name = os.path.basename(download_request.file_path)

        # Generate unique download key
        download_key = str(uuid.uuid4())

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=download_request.expires_in_days)

        # Create download record
        download = DownloadRecord(
            download_key=download_key,
            file_path=download_request.file_path,
            file_name=file_name,
            file_size=file_stat.st_size,
            description=download_request.description,
            created_by=current_user.id,
            expires_at=expires_at,
            download_count=0,
            is_active=True
        )

        db.add(download)
        await db.commit()
        await db.refresh(download)

        logger.info(f"Download link created: {download.id} - {download_key}")

        return DownloadRecordResponse(
            id=download.id,
            download_key=download.download_key,
            file_path=download.file_path,
            file_name=download.file_name,
            file_size=download.file_size,
            description=download.description,
            created_by=download.created_by,
            created_at=download.created_at,
            expires_at=download.expires_at,
            download_count=download.download_count,
            is_expired=download.expires_at < datetime.utcnow(),
            is_active=download.is_active
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{download_key}")
async def download_file(
    download_key: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Download file using download key

    No authentication required, but link expires after set time
    """
    try:
        # Get download record
        result = await db.execute(
            select(DownloadRecord).where(
                DownloadRecord.download_key == download_key,
                DownloadRecord.is_active == True
            )
        )
        download = result.scalar_one_or_none()

        if not download:
            raise HTTPException(status_code=404, detail="Download link not found")

        # Check expiration
        if download.expires_at < datetime.utcnow():
            download.is_active = False
            await db.commit()
            raise HTTPException(status_code=410, detail="Download link has expired")

        # Check file exists
        if not os.path.exists(download.file_path):
            raise HTTPException(status_code=404, detail="File no longer available")

        # Create download session
        session = DownloadSession(
            download_id=download.id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            completed=False
        )
        db.add(session)

        # Increment download count
        download.download_count += 1

        await db.commit()

        logger.info(f"File downloaded: {download.id} - {download.file_name}")

        # Return file
        return FileResponse(
            path=download.file_path,
            filename=download.file_name,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[DownloadRecordResponse])
async def list_downloads(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """List downloads created by current user"""
    try:
        # Build query
        query = select(DownloadRecord).where(
            DownloadRecord.created_by == current_user.id
        )

        if active_only:
            query = query.where(
                DownloadRecord.is_active == True,
                DownloadRecord.expires_at > datetime.utcnow()
            )

        query = query.order_by(DownloadRecord.created_at.desc())

        # Execute query
        result = await db.execute(query)
        downloads = result.scalars().all()

        # Format response
        download_list = []
        for dl in downloads:
            download_list.append(DownloadRecordResponse(
                id=dl.id,
                download_key=dl.download_key,
                file_path=dl.file_path,
                file_name=dl.file_name,
                file_size=dl.file_size,
                description=dl.description,
                created_by=dl.created_by,
                created_at=dl.created_at,
                expires_at=dl.expires_at,
                download_count=dl.download_count,
                is_expired=dl.expires_at < datetime.utcnow(),
                is_active=dl.is_active
            ))

        return download_list

    except Exception as e:
        logger.error(f"List downloads error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{download_id}")
async def delete_download(
    download_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a download link"""
    try:
        # Get download
        result = await db.execute(
            select(DownloadRecord).where(
                DownloadRecord.id == download_id,
                DownloadRecord.created_by == current_user.id
            )
        )
        download = result.scalar_one_or_none()

        if not download:
            raise HTTPException(status_code=404, detail="Download not found")

        # Deactivate
        download.is_active = False
        await db.commit()

        logger.info(f"Download deactivated: {download_id}")

        return {"success": True, "message": "Download link deactivated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=DownloadStatsResponse)
async def get_download_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get download statistics for current user"""
    try:
        # Total downloads
        total_result = await db.execute(
            select(func.count()).select_from(DownloadRecord)
            .where(DownloadRecord.created_by == current_user.id)
        )
        total_downloads = total_result.scalar()

        # Active downloads
        active_result = await db.execute(
            select(func.count()).select_from(DownloadRecord)
            .where(
                DownloadRecord.created_by == current_user.id,
                DownloadRecord.is_active == True,
                DownloadRecord.expires_at > datetime.utcnow()
            )
        )
        active_downloads = active_result.scalar()

        # Expired downloads
        expired_downloads = total_downloads - active_downloads

        # Total download count
        count_result = await db.execute(
            select(func.sum(DownloadRecord.download_count))
            .where(DownloadRecord.created_by == current_user.id)
        )
        total_download_count = count_result.scalar() or 0

        # Popular downloads
        popular_result = await db.execute(
            select(DownloadRecord)
            .where(DownloadRecord.created_by == current_user.id)
            .order_by(DownloadRecord.download_count.desc())
            .limit(5)
        )
        popular = popular_result.scalars().all()

        popular_downloads = []
        for dl in popular:
            popular_downloads.append({
                "id": dl.id,
                "file_name": dl.file_name,
                "download_count": dl.download_count,
                "created_at": dl.created_at.isoformat()
            })

        return DownloadStatsResponse(
            total_downloads=total_downloads,
            active_downloads=active_downloads,
            expired_downloads=expired_downloads,
            total_download_count=total_download_count,
            downloads_by_day={},  # TODO: Implement daily stats
            popular_downloads=popular_downloads
        )

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_downloads(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cleanup expired downloads

    This would normally be a scheduled task
    """
    try:
        # Find expired downloads
        result = await db.execute(
            select(DownloadRecord).where(
                DownloadRecord.expires_at < datetime.utcnow(),
                DownloadRecord.is_active == True
            )
        )
        expired = result.scalars().all()

        count = 0
        for download in expired:
            download.is_active = False
            count += 1

        await db.commit()

        logger.info(f"Cleaned up {count} expired downloads")

        return {"success": True, "cleaned": count}

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))