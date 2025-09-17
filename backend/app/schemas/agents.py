"""
Schemas for multi-agent system endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentQueryRequest(BaseModel):
    """Request for agent query"""
    query: str = Field(..., description="Query text")
    agent_type: Optional[str] = Field(None, description="Specific agent to use (knight, bard, wizard)")
    chat_history: Optional[List[Dict[str, str]]] = Field(default=[], description="Previous chat messages")
    language: Optional[str] = Field("pt", description="Response language")
    context: Optional[str] = Field(None, description="Additional context for the query")


class AgentQueryResponse(BaseModel):
    """Response from agent query"""
    success: bool = True
    query: str
    response: str
    agent_used: str
    reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    llm_provider: Optional[str] = None
    response_time_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    """Information about a single agent"""
    name: str
    display_name: str
    description: str
    capabilities: List[str]
    languages: List[str]
    is_default: bool = False


class AgentListResponse(BaseModel):
    """Response containing list of available agents"""
    agents: List[AgentInfo]
    total: int