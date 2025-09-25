"""
Knowledge Resources models for contextual links and documents
"""
import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, UniqueConstraint, event
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UsefulLink(Base):
    __tablename__ = "useful_links"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Descriptive title
    url = Column(String(500), nullable=False)  # Link URL
    description = Column(Text, default="")  # Content description for users
    ai_guidance = Column(Text, default="")  # Guidelines for AI on when to share this link
    category = Column(String(100), nullable=True)  # Legacy category field (to be deprecated)
    category_id = Column(Integer, ForeignKey("resource_categories.id", ondelete="SET NULL"), nullable=True)  # FK to resource_categories

    # Status and control
    is_active = Column(Boolean, default=True)  # If the link is active to be shared

    # Usage metrics
    send_count = Column(Integer, default=0)  # Number of times the link was sent by AI

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Tags for better organization
    tags = Column(JSON, default=list)  # Tags for search and organization

    # Relationships
    created_by = relationship("User")
    resource_category = relationship("ResourceCategory", back_populates="useful_links")

    # Indexes
    __table_args__ = (
        Index('ix_useful_links_category', 'category'),
        Index('ix_useful_links_category_id', 'category_id'),
        Index('ix_useful_links_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<UsefulLink(id={self.id}, title='{self.title}', category='{self.category}')>"


class DownloadableDocument(Base):
    __tablename__ = "downloadable_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Document title
    description = Column(Text, default="")  # Document description and usage
    ai_guidance = Column(Text, default="")  # Guidelines for AI on when to provide this document
    category = Column(String(100), nullable=True)  # Legacy category field (to be deprecated)
    category_id = Column(Integer, ForeignKey("resource_categories.id", ondelete="SET NULL"), nullable=True)  # FK to resource_categories

    # File information
    file = Column(String(500), nullable=False)  # File path
    file_name = Column(String(255), nullable=False)  # Original file name
    file_size = Column(BigInteger, nullable=False)  # File size in bytes
    file_type = Column(String(50), nullable=False)  # File type (pdf, docx, xlsx, etc.)

    # Status and control
    is_active = Column(Boolean, default=True)  # If the document is active for download

    # Usage metrics
    download_count = Column(Integer, default=0)  # Number of times downloaded
    share_count = Column(Integer, default=0)  # Number of times shared by AI

    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Tags for better organization
    tags = Column(JSON, default=list)  # Tags for search and organization

    # Access configurations
    requires_approval = Column(Boolean, default=False)  # If requires approval before download
    expiry_date = Column(DateTime, nullable=True)  # Document expiry date

    # Relationships
    created_by = relationship("User")
    resource_category = relationship("ResourceCategory", back_populates="downloadable_documents")

    # Indexes
    __table_args__ = (
        Index('ix_downloadable_docs_category', 'category'),
        Index('ix_downloadable_docs_category_id', 'category_id'),
        Index('ix_downloadable_docs_is_active', 'is_active'),
        Index('ix_downloadable_docs_file_type', 'file_type'),
    )

    def __repr__(self):
        return f"<DownloadableDocument(id={self.id}, title='{self.title}', file_type='{self.file_type}')>"

    def update_file_metadata(self):
        """Update file metadata from the file"""
        if self.file:
            if not self.file_name:
                self.file_name = os.path.basename(self.file)
            if not self.file_type:
                self.file_type = os.path.splitext(self.file)[1][1:].lower()
            # Note: file_size should be set when uploading the file


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    color_code = Column(String(7), default="")  # Hex color code for UI (#FFFFFF)
    icon = Column(String(50), default="")  # Icon name for UI

    # Display order
    order = Column(Integer, default=0)  # Display order (lower value appears first)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    useful_links = relationship("UsefulLink", back_populates="resource_category")
    downloadable_documents = relationship("DownloadableDocument", back_populates="resource_category")

    # Indexes
    __table_args__ = (
        Index('ix_resource_categories_order', 'order'),
    )

    def __repr__(self):
        return f"<ResourceCategory(id={self.id}, name='{self.name}')>"


class ResourceUsage(Base):
    __tablename__ = "resource_usage"

    # Resource types
    RESOURCE_TYPE_LINK = 'link'
    RESOURCE_TYPE_DOCUMENT = 'document'

    # Action types
    ACTION_SHARED = 'shared'
    ACTION_CLICKED = 'clicked'
    ACTION_DOWNLOADED = 'downloaded'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resource_type = Column(String(20), nullable=False)
    resource_id = Column(Integer, nullable=False)  # ID of the link or document
    action = Column(String(20), nullable=False)

    # Context
    chat_session_id = Column(Integer, nullable=True)  # Related chat session ID
    query_context = Column(Text, default="")  # Context of the question that led to the action

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index('ix_resource_usage_resource', 'resource_type', 'resource_id'),
        Index('ix_resource_usage_user_action', 'user_id', 'action'),
        Index('ix_resource_usage_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ResourceUsage(id={self.id}, resource_type='{self.resource_type}', action='{self.action}')>"

    @property
    def resource_type_display(self):
        """Get human-readable resource type"""
        type_map = {
            self.RESOURCE_TYPE_LINK: 'Link Útil',
            self.RESOURCE_TYPE_DOCUMENT: 'Documento',
        }
        return type_map.get(self.resource_type, self.resource_type)

    @property
    def action_display(self):
        """Get human-readable action"""
        action_map = {
            self.ACTION_SHARED: 'Compartilhado pela IA',
            self.ACTION_CLICKED: 'Clicado pelo usuário',
            self.ACTION_DOWNLOADED: 'Baixado pelo usuário',
        }
        return action_map.get(self.action, self.action)


# Event listener to update file metadata before insert/update
@event.listens_for(DownloadableDocument, "before_insert")
@event.listens_for(DownloadableDocument, "before_update")
def update_document_metadata(mapper, connection, target):
    """Update file metadata before saving"""
    target.update_file_metadata()