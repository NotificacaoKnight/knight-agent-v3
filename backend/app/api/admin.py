"""
Admin management API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import logging

from app.api.deps import get_async_db, get_current_user
from app.models.user import User
from app.core.admin_config import admin_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)


class AdminEmailRequest(BaseModel):
    """Request model for adding admin email"""
    email: EmailStr


class AdminEmailResponse(BaseModel):
    """Response model for admin email"""
    email: str
    added_by: str
    is_active: bool


class AdminListResponse(BaseModel):
    """Response model for admin email list"""
    admins: List[str]
    count: int


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin privileges

    Args:
        current_user: Current authenticated user

    Returns:
        User if admin, raises HTTPException otherwise
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/list", response_model=AdminListResponse)
async def list_admins(
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    List all admin emails

    Requires admin privileges
    """
    try:
        admins = await admin_service.get_admin_emails(db)
        return AdminListResponse(
            admins=admins,
            count=len(admins)
        )
    except Exception as e:
        logger.error(f"Error listing admins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admin list"
        )


@router.post("/add", response_model=dict)
async def add_admin(
    request: AdminEmailRequest,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    Add a new admin email

    Requires admin privileges
    """
    try:
        # Add admin email
        success = await admin_service.add_admin_email(
            email=request.email,
            added_by=admin_user.email,
            db=db
        )

        if not success:
            return {
                "success": False,
                "message": f"Email {request.email} is already an admin"
            }

        return {
            "success": True,
            "message": f"Successfully added {request.email} as admin",
            "email": request.email
        }

    except Exception as e:
        logger.error(f"Error adding admin {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add admin"
        )


@router.delete("/remove/{email}", response_model=dict)
async def remove_admin(
    email: str,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    Remove admin privileges from an email

    Requires admin privileges
    Cannot remove yourself or the last admin
    """
    try:
        # Prevent self-removal
        if email.lower() == admin_user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove your own admin privileges"
            )

        # Remove admin email
        success = await admin_service.remove_admin_email(
            email=email,
            removed_by=admin_user.email,
            db=db
        )

        if not success:
            return {
                "success": False,
                "message": f"Failed to remove {email}. Cannot remove the last admin."
            }

        return {
            "success": True,
            "message": f"Successfully removed admin privileges from {email}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing admin {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove admin"
        )


@router.get("/check/{email}", response_model=dict)
async def check_admin(
    email: str,
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    Check if an email has admin privileges

    Requires admin privileges
    """
    try:
        is_admin = await admin_service.is_admin_email(email, db)
        return {
            "email": email,
            "is_admin": is_admin
        }
    except Exception as e:
        logger.error(f"Error checking admin status for {email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check admin status"
        )


@router.post("/sync", response_model=dict)
async def sync_admins(
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(require_admin)
):
    """
    Sync initial admin emails to database
    This ensures the initial admin list is properly configured

    Requires admin privileges
    """
    try:
        await admin_service.sync_initial_admins(db)
        admins = await admin_service.get_admin_emails(db)

        return {
            "success": True,
            "message": "Admin list synchronized",
            "admins": admins
        }
    except Exception as e:
        logger.error(f"Error syncing admins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync admin list"
        )