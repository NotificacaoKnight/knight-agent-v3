"""
Pydantic schemas for Knowledge Resources endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class UsefulLinkCreate(BaseModel):
    """Create useful link"""
    title: str = Field(..., description="Link title")
    url: HttpUrl = Field(..., description="Link URL")
    description: str = Field(..., description="Link description")
    category_id: Optional[int] = Field(None, description="Category ID")
    ai_guidance: Optional[str] = Field(None, description="AI guidance for when to suggest this link")
    tags: Optional[List[str]] = Field(None, description="Link tags")
    is_active: bool = Field(True, description="Is link active")


class UsefulLinkResponse(BaseModel):
    """Useful link response"""
    id: int
    title: str
    url: str
    description: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    ai_guidance: Optional[str] = None
    tags: List[str] = []
    send_count: int
    click_count: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime


class DownloadableDocumentCreate(BaseModel):
    """Create downloadable document"""
    title: str = Field(..., description="Document title")
    file_path: str = Field(..., description="File path")
    description: str = Field(..., description="Document description")
    category_id: Optional[int] = Field(None, description="Category ID")
    ai_guidance: Optional[str] = Field(None, description="AI guidance for when to suggest this document")
    tags: Optional[List[str]] = Field(None, description="Document tags")
    is_active: bool = Field(True, description="Is document active")


class DownloadableDocumentResponse(BaseModel):
    """Downloadable document response"""
    id: int
    title: str
    file_path: str
    file_name: str
    file_size: int
    description: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    ai_guidance: Optional[str] = None
    tags: List[str] = []
    download_count: int
    send_count: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime


class ResourceCategoryCreate(BaseModel):
    """Create resource category"""
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(None, description="Category icon")
    color: Optional[str] = Field(None, description="Category color")
    is_active: bool = Field(True, description="Is category active")


class ResourceCategoryResponse(BaseModel):
    """Resource category response"""
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    link_count: int = 0
    document_count: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceUsageResponse(BaseModel):
    """Resource usage tracking"""
    id: int
    resource_type: str
    resource_id: int
    action: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    created_at: datetime


class KnowledgeSearchQuery(BaseModel):
    """Knowledge resources search query"""
    query: str = Field(..., description="Search query")
    resource_type: Optional[str] = Field(None, description="Filter by resource type (links/documents)")
    category_id: Optional[int] = Field(None, description="Filter by category")
    limit: int = Field(10, description="Maximum results", ge=1, le=50)


class KnowledgeSearchResponse(BaseModel):
    """Knowledge resources search response"""
    links: List[UsefulLinkResponse] = []
    documents: List[DownloadableDocumentResponse] = []
    total_links: int = 0
    total_documents: int = 0
    search_time_ms: int = 0