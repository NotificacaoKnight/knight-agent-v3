"""
Pydantic schemas for Document endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """Document upload request"""
    title: str = Field(..., description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    category: Optional[str] = Field(None, description="Document category")
    tags: Optional[List[str]] = Field(None, description="Document tags")


class DocumentResponse(BaseModel):
    """Document response"""
    id: int
    title: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    chunk_count: int = 0
    processing_status: str
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_by: int
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    """Document chunk response"""
    id: int
    document_id: int
    chunk_index: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime


class ProcessingJobResponse(BaseModel):
    """Processing job response"""
    id: int
    document_id: int
    status: str
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DocumentStatsResponse(BaseModel):
    """Document statistics response"""
    total_documents: int
    processed_documents: int
    processing_documents: int
    failed_documents: int
    total_chunks: int
    total_embeddings: int
    storage_size_mb: float
    average_processing_time_sec: Optional[float] = None
    documents_by_type: Dict[str, int] = {}
    documents_by_status: Dict[str, int] = {}


class DocumentSearchQuery(BaseModel):
    """Document search query"""
    query: str = Field(..., description="Search query")
    document_ids: Optional[List[int]] = Field(None, description="Filter by document IDs")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(10, description="Maximum results", ge=1, le=100)
    offset: int = Field(0, description="Offset for pagination", ge=0)
    include_content: bool = Field(False, description="Include full document content")


class DocumentSearchResponse(BaseModel):
    """Document search response"""
    documents: List[DocumentResponse]
    total_count: int
    has_more: bool
    search_time_ms: int


class BulkOperationRequest(BaseModel):
    """Bulk operation request"""
    document_ids: List[int] = Field(..., description="Document IDs to operate on")
    operation: str = Field(..., description="Operation to perform (delete, reprocess, tag)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    success_count: int
    failure_count: int
    failed_ids: List[int] = []
    errors: Dict[int, str] = {}
    operation_time_ms: int