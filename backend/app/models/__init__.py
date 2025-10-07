"""
Application models
Import all models here to ensure they're registered with SQLAlchemy
"""
from app.models.user import User, UserSession
from app.models.admin import AdminEmail
from app.models.document import Document, DocumentChunk, ProcessingJob
from app.models.chat import (
    ChatSession, ChatMessage, DocumentRequest,
    LinkRequest, ChatFeedback
)
from app.models.knowledge import (
    UsefulLink, DownloadableDocument,
    ResourceCategory, ResourceUsage
)
from app.models.downloads import DownloadRecord, DownloadSession
from app.models.rag import RAGQueryLog

__all__ = [
    # User models
    "User",
    "UserSession",
    # Admin models
    "AdminEmail",
    # RAG models
    "RAGQueryLog",
    # Document models
    "Document",
    "DocumentChunk",
    "ProcessingJob",
    # Chat models
    "ChatSession",
    "ChatMessage",
    "DocumentRequest",
    "LinkRequest",
    "ChatFeedback",
    # Knowledge resources models
    "UsefulLink",
    "DownloadableDocument",
    "ResourceCategory",
    "ResourceUsage",
    # Downloads models
    "DownloadRecord",
    "DownloadSession",
]