"""
Chat models for conversation management and AI interactions
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Float,
    Text, JSON, ForeignKey, Index, event
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timezone_utils import utc_now


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="")

    # Session configuration fields
    context = Column(Text, default="")  # Initial context for the session
    language = Column(String(10), default="pt")  # Session language (pt, en, es)
    agent_type = Column(String(20), nullable=True)  # Preferred agent (knight, wizard, bard)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    is_active = Column(Boolean, default=True)

    # Session metadata
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    document_requests = relationship("DocumentRequest", back_populates="session", cascade="all, delete-orphan")
    link_requests = relationship("LinkRequest", back_populates="session", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_chat_sessions_user_id', 'user_id'),
        Index('ix_chat_sessions_updated_at', 'updated_at'),
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    # Message types
    MESSAGE_TYPE_USER = 'user'
    MESSAGE_TYPE_ASSISTANT = 'assistant'
    MESSAGE_TYPE_SYSTEM = 'system'

    # Content types
    CONTENT_TYPE_TEXT = 'text'
    CONTENT_TYPE_AUDIO = 'audio'

    # Agent types
    AGENT_TYPE_KNIGHT = 'knight'
    AGENT_TYPE_WIZARD = 'wizard'
    AGENT_TYPE_BARD = 'bard'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(String(10), nullable=False)
    content_type = Column(String(10), default=CONTENT_TYPE_TEXT)
    content = Column(Text, nullable=False)

    # Multi-agent system fields
    agent_type = Column(String(10), default=AGENT_TYPE_KNIGHT)
    is_handoff = Column(Boolean, default=False)  # True if transition message

    # Audio message fields
    audio_file = Column(String(500), nullable=True)  # Path to audio file
    audio_duration = Column(Float, nullable=True)  # Duration in seconds
    transcription = Column(Text, default="")

    # Assistant message metadata
    context_used = Column(JSON, default=list)  # Chunks used as context
    search_query_id = Column(Integer, nullable=True)  # RAG search ID
    llm_provider = Column(String(20), default="")
    llm_model = Column(String(50), default="")

    # Suggested useful resources
    useful_links = Column(JSON, default=list)  # Useful links included in response
    downloadable_documents = Column(JSON, default=list)  # Documents for download

    # Performance
    response_time_ms = Column(Integer, nullable=True)

    # Message status
    is_helpful = Column(Boolean, nullable=True)  # User feedback

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Generic metadata (for additional information like language, provider details, etc.)
    message_metadata = Column(JSON, nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    document_requests = relationship("DocumentRequest", back_populates="message", cascade="all, delete-orphan")
    link_requests = relationship("LinkRequest", back_populates="message", cascade="all, delete-orphan")
    feedback = relationship("ChatFeedback", back_populates="message", uselist=False, cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_chat_messages_session_id', 'session_id'),
        Index('ix_chat_messages_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, type='{self.message_type}')>"

    @property
    def message_type_display(self):
        """Get human-readable message type"""
        type_map = {
            self.MESSAGE_TYPE_USER: 'Usuário',
            self.MESSAGE_TYPE_ASSISTANT: 'Assistente',
            self.MESSAGE_TYPE_SYSTEM: 'Sistema',
        }
        return type_map.get(self.message_type, self.message_type)

    @property
    def content_type_display(self):
        """Get human-readable content type"""
        type_map = {
            self.CONTENT_TYPE_TEXT: 'Texto',
            self.CONTENT_TYPE_AUDIO: 'Áudio',
        }
        return type_map.get(self.content_type, self.content_type)

    @property
    def agent_type_display(self):
        """Get human-readable agent type"""
        type_map = {
            self.AGENT_TYPE_KNIGHT: 'Knight',
            self.AGENT_TYPE_WIZARD: 'Wizard',
            self.AGENT_TYPE_BARD: 'Bard',
        }
        return type_map.get(self.agent_type, self.agent_type)


class DocumentRequest(Base):
    __tablename__ = "document_requests"

    # Status choices
    STATUS_REQUESTED = 'requested'
    STATUS_FOUND = 'found'
    STATUS_NOT_FOUND = 'not_found'
    STATUS_DOWNLOADED = 'downloaded'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)

    document_name = Column(String(255), nullable=False)
    document_id = Column(Integer, nullable=True)  # Document ID if found

    status = Column(String(20), default=STATUS_REQUESTED)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="document_requests")
    message = relationship("ChatMessage", back_populates="document_requests")

    def __repr__(self):
        return f"<DocumentRequest(id={self.id}, document_name='{self.document_name}', status='{self.status}')>"

    @property
    def status_display(self):
        """Get human-readable status"""
        status_map = {
            self.STATUS_REQUESTED: 'Solicitado',
            self.STATUS_FOUND: 'Encontrado',
            self.STATUS_NOT_FOUND: 'Não Encontrado',
            self.STATUS_DOWNLOADED: 'Baixado',
        }
        return status_map.get(self.status, self.status)


class LinkRequest(Base):
    __tablename__ = "link_requests"

    # Status choices
    STATUS_SENT = 'sent'
    STATUS_CLICKED = 'clicked'
    STATUS_NOT_RELEVANT = 'not_relevant'

    # User feedback choices
    FEEDBACK_HELPFUL = 'helpful'
    FEEDBACK_NOT_HELPFUL = 'not_helpful'
    FEEDBACK_IRRELEVANT = 'irrelevant'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)

    link_title = Column(String(255), nullable=False)
    link_url = Column(String(500), nullable=False)
    link_id = Column(Integer, nullable=True)  # Useful link ID if found in system

    # Request context
    request_context = Column(Text, default="")  # Context of the question that led to the link

    status = Column(String(20), default=STATUS_SENT)

    # Metadata for analysis
    ai_confidence = Column(Float, nullable=True)  # AI confidence in link relevance (0-1)
    user_feedback = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="link_requests")
    message = relationship("ChatMessage", back_populates="link_requests")

    def __repr__(self):
        return f"<LinkRequest(id={self.id}, link_title='{self.link_title}', status='{self.status}')>"

    @property
    def status_display(self):
        """Get human-readable status"""
        status_map = {
            self.STATUS_SENT: 'Enviado',
            self.STATUS_CLICKED: 'Clicado',
            self.STATUS_NOT_RELEVANT: 'Não Relevante',
        }
        return status_map.get(self.status, self.status)

    @property
    def user_feedback_display(self):
        """Get human-readable user feedback"""
        feedback_map = {
            self.FEEDBACK_HELPFUL: 'Útil',
            self.FEEDBACK_NOT_HELPFUL: 'Não Útil',
            self.FEEDBACK_IRRELEVANT: 'Irrelevante',
        }
        return feedback_map.get(self.user_feedback, '')


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"

    # Rating choices
    RATING_POSITIVE = 'positive'
    RATING_NEGATIVE = 'negative'

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    rating = Column(String(20), default=RATING_POSITIVE)
    comment = Column(Text, default="")  # Optional comment about the feedback

    # Reference to RAG search if applicable
    search_query_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    message = relationship("ChatMessage", back_populates="feedback")
    user = relationship("User")

    def __repr__(self):
        return f"<ChatFeedback(id={self.id}, message_id={self.message_id}, rating='{self.rating}')>"

    @property
    def rating_display(self):
        """Get human-readable rating"""
        rating_map = {
            self.RATING_POSITIVE: 'Positivo',
            self.RATING_NEGATIVE: 'Negativo',
        }
        return rating_map.get(self.rating, self.rating)