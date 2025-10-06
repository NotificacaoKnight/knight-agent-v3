"""
Pydantic schemas for Document endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.base import (
    TimezoneResponseModel,
    PaginatedResponse,
    TimezoneAwareDatetime,
    OptionalTimezoneAwareDatetime
)


class DocumentUpload(BaseModel):
    """Document upload request"""
    title: str = Field(..., description="Document title")
    enable_ocr: bool = Field(False, description="Enable OCR for scanned documents")
    chunk_size: Optional[int] = Field(None, description="Custom chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Custom chunk overlap")
    language: str = Field("pt", description="Document language")
    tags: Optional[List[str]] = Field(None, description="Document tags")


class DocumentResponse(TimezoneResponseModel):
    """Document response with timezone-aware timestamps"""
    id: int
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    created_at: datetime = TimezoneAwareDatetime
    updated_at: datetime = TimezoneAwareDatetime
    processing_started_at: Optional[datetime] = OptionalTimezoneAwareDatetime
    processing_completed_at: Optional[datetime] = OptionalTimezoneAwareDatetime
    error_message: Optional[str] = None
    document_metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    access_count: int = 0
    uploaded_by_name: Optional[str] = None
    uploaded_by_email: Optional[str] = None


class DocumentListResponse(PaginatedResponse):
    """Document list response with pagination and timezone support"""
    documents: List[DocumentResponse]

    def __init__(self, **data):
        # Ensure 'items' is set to same as 'documents' for PaginatedResponse
        if 'documents' in data and 'items' not in data:
            data['items'] = data['documents']
        elif 'items' in data and 'documents' not in data:
            data['documents'] = data['items']
        super().__init__(**data)


class ChunkResponse(BaseModel):
    """Document chunk response"""
    id: int
    document_id: int
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    has_embedding: bool
    chunk_metadata: Optional[Dict[str, Any]] = None


class ProcessingJobResponse(TimezoneResponseModel):
    """Processing job response with timezone-aware timestamps"""
    id: int
    document_id: int
    job_type: str
    status: str
    progress: Optional[float] = None
    created_at: datetime = TimezoneAwareDatetime
    started_at: Optional[datetime] = OptionalTimezoneAwareDatetime
    completed_at: Optional[datetime] = OptionalTimezoneAwareDatetime
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class DocumentStatsResponse(BaseModel):
    """Document statistics response"""
    total_documents: int
    processed_documents: int
    pending_documents: int
    processing_documents: int
    error_documents: int
    downloadable_documents: int
    total_chunks: int


class DeleteDocumentResponse(BaseModel):
    """Delete document response"""
    success: bool
    message: str
    document_id: int
    chunks_deleted: int
    files_deleted: List[str]


class DocumentContentResponse(BaseModel):
    """Document content response"""
    title: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    chunks_count: int