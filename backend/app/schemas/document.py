"""
Pydantic schemas for Document endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """Document upload request"""
    title: str = Field(..., description="Document title")
    enable_ocr: bool = Field(False, description="Enable OCR for scanned documents")
    chunk_size: Optional[int] = Field(None, description="Custom chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Custom chunk overlap")
    language: str = Field("pt", description="Document language")
    tags: Optional[List[str]] = Field(None, description="Document tags")


class DocumentResponse(BaseModel):
    """Document response"""
    id: int
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    document_metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = []


class DocumentListResponse(BaseModel):
    """Document list response"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


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


class ProcessingJobResponse(BaseModel):
    """Processing job response"""
    id: int
    document_id: int
    job_type: str
    status: str
    progress: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class DocumentStatsResponse(BaseModel):
    """Document statistics response"""
    total_documents: int
    total_chunks: int
    documents_by_status: Dict[str, int]
    documents_by_type: Dict[str, int]
    total_size_bytes: int
    processing_jobs: Dict[str, int]
    average_chunks_per_document: float
    documents_with_errors: int


class DeleteDocumentResponse(BaseModel):
    """Delete document response"""
    success: bool
    message: str
    document_id: int
    chunks_deleted: int
    files_deleted: List[str]