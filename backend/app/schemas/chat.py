"""
Pydantic schemas for Chat endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    """Create chat message"""
    content: str = Field(..., description="Message content")
    message_type: str = Field("user", description="Message type (user/assistant)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: int
    session_id: int
    content: str
    message_type: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    feedback_score: Optional[int] = None
    feedback_text: Optional[str] = None


class ChatSessionCreate(BaseModel):
    """Create chat session"""
    title: Optional[str] = Field(None, description="Session title")
    context: Optional[str] = Field(None, description="Initial context")
    language: str = Field("pt", description="Session language")
    agent_type: Optional[str] = Field(None, description="Preferred agent type")


class ChatSessionResponse(BaseModel):
    """Chat session response"""
    id: int
    user_id: int
    title: Optional[str] = None
    context: Optional[str] = None
    language: str
    agent_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    is_active: bool = True


class ChatSessionListResponse(BaseModel):
    """Chat session list response"""
    sessions: List[ChatSessionResponse]
    total: int
    page: int
    page_size: int


class ChatQueryRequest(BaseModel):
    """Chat query request"""
    query: str = Field(..., description="User query")
    session_id: Optional[int] = Field(None, description="Chat session ID")
    use_rag: bool = Field(True, description="Use RAG for response")
    use_agentic: bool = Field(False, description="Use agentic RAG")
    stream: bool = Field(False, description="Stream response")
    language: str = Field("pt", description="Response language")
    max_tokens: int = Field(1000, description="Maximum tokens in response")
    temperature: float = Field(0.7, description="Generation temperature")


class ChatQueryResponse(BaseModel):
    """Chat query response"""
    success: bool
    session_id: int
    message_id: int
    query: str
    response: str
    sources: List[Dict[str, Any]] = []
    agent_used: Optional[str] = None
    llm_provider: str
    response_time_ms: int
    metadata: Dict[str, Any] = {}


class ChatFeedbackRequest(BaseModel):
    """Chat feedback request"""
    message_id: int = Field(..., description="Message ID to provide feedback for")
    score: int = Field(..., description="Feedback score (1-5)", ge=1, le=5)
    text: Optional[str] = Field(None, description="Optional feedback text")


class ChatFeedbackResponse(BaseModel):
    """Chat feedback response"""
    success: bool
    message_id: int
    feedback_id: int


class DocumentRequestCreate(BaseModel):
    """Document request in chat"""
    message_id: int = Field(..., description="Related message ID")
    document_ids: List[int] = Field(..., description="Requested document IDs")
    request_type: str = Field("reference", description="Request type (reference/download)")


class LinkRequestCreate(BaseModel):
    """Link request in chat"""
    message_id: int = Field(..., description="Related message ID")
    link_ids: List[int] = Field(..., description="Requested link IDs")


class ChatHistoryResponse(BaseModel):
    """Chat history with messages"""
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
    has_more: bool
    total_messages: int