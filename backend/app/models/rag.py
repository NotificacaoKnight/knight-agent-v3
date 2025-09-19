"""
RAG (Retrieval-Augmented Generation) models
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class RAGQueryLog(Base):
    """
    Log of RAG queries for metrics and monitoring
    """
    __tablename__ = "rag_query_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Query information
    query = Column(Text, nullable=False)
    response = Column(Text)

    # Provider information
    provider = Column(String(50))
    model = Column(String(100))

    # Performance metrics
    response_time = Column(Float)  # in seconds
    tokens_used = Column(Integer)

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # User information
    user_id = Column(Integer, index=True)
    session_id = Column(String(255))

    # Query metadata
    query_metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RAGQueryLog(id={self.id}, provider={self.provider}, success={self.success})>"