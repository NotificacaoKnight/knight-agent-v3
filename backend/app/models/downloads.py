"""
Downloads models for FastAPI
Migrated from Django downloads app
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
import os

from app.core.database import Base
from app.core.config import settings


class DownloadRecord(Base):
    __tablename__ = "download_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Download metadata
    download_token = Column(String(64), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    downloaded_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    download_count = Column(Integer, default=0)

    # User IP
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User")
    document = relationship("Document")

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'document_id', 'created_at', name='uq_user_document_created'),
        Index('ix_download_records_user_id', 'user_id'),
        Index('ix_download_records_document_id', 'document_id'),
        Index('ix_download_records_expires_at', 'expires_at'),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set expiry date if not provided
        if not self.expires_at:
            retention_days = settings.DOWNLOADS_RETENTION_DAYS
            self.expires_at = datetime.utcnow() + timedelta(days=retention_days)

    def __repr__(self):
        return f"<DownloadRecord(id={self.id}, user_id={self.user_id}, file_name='{self.file_name}')>"

    @property
    def is_expired(self) -> bool:
        """Check if download link has expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining until expiry"""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - datetime.utcnow()

    @property
    def time_remaining_str(self) -> str:
        """Get human-readable time remaining"""
        remaining = self.time_remaining
        if remaining.total_seconds() <= 0:
            return "Expired"

        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} dia{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:  # Only show minutes if no days
            parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")

        return " ".join(parts) if parts else "Less than a minute"


class DownloadSession(Base):
    __tablename__ = "download_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(64), unique=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_access = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Metadata
    downloads_count = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), default="")

    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('ix_download_sessions_user_id', 'user_id'),
        Index('ix_download_sessions_last_access', 'last_access'),
    )

    def __repr__(self):
        return f"<DownloadSession(id={self.id}, user_id={self.user_id}, token='{self.session_token[:10]}...')>"

    def update_access(self):
        """Update last access time and increment download count"""
        self.last_access = datetime.utcnow()
        self.downloads_count += 1