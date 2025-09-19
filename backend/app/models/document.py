"""
Document models for document processing and RAG system
"""
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, UniqueConstraint, event
)
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Try to import pgvector, but make it optional
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    # Create a dummy Vector type for development without pgvector
    Vector = lambda dim: JSON
import logging

from app.core.database import Base

logger = logging.getLogger(__name__)


class Document(Base):
    __tablename__ = "documents"

    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_PROCESSED = 'processed'
    STATUS_ERROR = 'error'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Store path instead of FileField
    processed_path = Column(String(500), default="")
    markdown_content = Column(Text, default="")
    file_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)

    status = Column(String(20), default=STATUS_PENDING, nullable=False)
    processing_error = Column(Text, default="")

    is_downloadable = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Foreign key to User
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata extracted from document (renamed from 'metadata' which is reserved in SQLAlchemy)
    document_metadata = Column(JSON, default=dict)

    # Access counter for ranking
    access_count = Column(Integer, default=0)

    # Relationships
    uploaded_by = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}')>"

    @property
    def status_display(self):
        """Get human-readable status"""
        status_map = {
            self.STATUS_PENDING: 'Pendente',
            self.STATUS_PROCESSING: 'Processando',
            self.STATUS_PROCESSED: 'Processado',
            self.STATUS_ERROR: 'Erro',
        }
        return status_map.get(self.status, self.status)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # pgvector field - BGE-m3 uses 1024 dimensions
    embedding = Column(Vector(1024), nullable=True)

    # Keep JSON backup for compatibility during migration
    embedding_json = Column(JSON, nullable=True)

    chunk_size = Column(Integer, nullable=False)
    start_position = Column(Integer, default=0)
    end_position = Column(Integer, default=0)

    # Chunk metadata
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), default="")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Indexes
    __table_args__ = (
        UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk'),
        Index('ix_document_chunks_document_id', 'document_id'),
        Index('ix_document_chunks_chunk_index', 'chunk_index'),
        # Vector similarity index will be created via Alembic migration
        # Index('ix_document_chunks_embedding_hnsw', 'embedding', postgresql_using='hnsw')
    )

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    # Status choices
    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    # Job types
    JOB_TYPE_MARKDOWN = 'markdown_conversion'
    JOB_TYPE_CHUNKING = 'chunking'
    JOB_TYPE_EMBEDDING = 'embedding'

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(50), nullable=False)
    status = Column(String(20), default=STATUS_QUEUED, nullable=False)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, default="")

    # Job configuration
    config = Column(JSON, default=dict)

    # Job results
    result = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="processing_jobs")

    # Indexes
    __table_args__ = (
        Index('ix_processing_jobs_document_id', 'document_id'),
        Index('ix_processing_jobs_status', 'status'),
        Index('ix_processing_jobs_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, document_id={self.document_id}, job_type='{self.job_type}', status='{self.status}')>"

    @property
    def status_display(self):
        """Get human-readable status"""
        status_map = {
            self.STATUS_QUEUED: 'Na Fila',
            self.STATUS_PROCESSING: 'Processando',
            self.STATUS_COMPLETED: 'Concluído',
            self.STATUS_FAILED: 'Falhado',
        }
        return status_map.get(self.status, self.status)


# Event listener for document deletion cleanup
@event.listens_for(Document, "after_delete")
def cleanup_document_files(mapper, connection, target):
    """
    Complete cleanup after document deletion - files, embeddings, caches, and indices
    This is the SQLAlchemy equivalent of Django's post_delete signal
    """
    try:
        doc_id = target.id
        doc_title = target.title
        logger.info(f"Starting COMPLETE cleanup for deleted document {doc_id}: {doc_title}")

        files_cleaned = []

        # 1. Remove original file
        if target.file_path:
            try:
                file_path = target.file_path
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_cleaned.append(f"Original: {file_path}")
                    logger.info(f"Original file removed: {file_path}")
            except Exception as file_error:
                logger.warning(f"Could not remove original file: {file_error}")

        # 2. Remove processed directory
        processed_paths_to_try = [
            target.processed_path,
            f"/home/felipealbertuxd/knight-agent/backend/processed_documents/{doc_id}/",
            f"processed_documents/{doc_id}/"
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
                    files_cleaned.append(f"Processed: {processed_dir}")
                    logger.info(f"Processed directory removed: {processed_dir}")
                    break

            except Exception as dir_error:
                logger.warning(f"Could not remove processed directory {processed_path}: {dir_error}")

        # 3. Cleanup embeddings and caches
        # TODO: Implement vector store cleanup once RAG services are migrated
        # This will be implemented in Phase 6 with the RAG system migration

        # 4. Final cleanup log
        logger.info(f"COMPLETE cleanup finished for document {doc_id}. Files cleaned: {files_cleaned}")
        print(f"✅ LIMPEZA COMPLETA do documento {doc_id}: {len(files_cleaned)} arquivos removidos")

    except Exception as e:
        logger.error(f"CRITICAL: Complete cleanup failed for document {getattr(target, 'id', 'unknown')}: {e}")
        print(f"❌ Erro crítico na limpeza completa: {e}")