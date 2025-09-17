"""
Pydantic schemas for Downloads endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DownloadRequestCreate(BaseModel):
    """Create download request"""
    file_path: str = Field(..., description="File path to make available for download")
    description: Optional[str] = Field(None, description="Download description")
    expires_in_days: int = Field(7, description="Days until expiration", ge=1, le=30)


class DownloadRecordResponse(BaseModel):
    """Download record response"""
    id: int
    download_key: str
    file_path: str
    file_name: str
    file_size: int
    description: Optional[str] = None
    created_by: int
    created_at: datetime
    expires_at: datetime
    download_count: int
    is_expired: bool
    is_active: bool


class DownloadSessionResponse(BaseModel):
    """Download session response"""
    id: int
    download_id: int
    accessed_at: datetime
    ip_address: str
    user_agent: Optional[str] = None
    completed: bool


class DownloadStatsResponse(BaseModel):
    """Download statistics"""
    total_downloads: int
    active_downloads: int
    expired_downloads: int
    total_download_count: int
    downloads_by_day: Dict[str, int]
    popular_downloads: List[Dict[str, Any]]