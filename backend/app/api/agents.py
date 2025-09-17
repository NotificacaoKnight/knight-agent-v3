"""
Multi-agent system API endpoints for FastAPI
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user, get_optional_current_user
from app.models.user import User
from app.schemas.agents import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentListResponse,
    AgentInfo
)
from app.services.rag.multi_agent_service import multi_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["multi-agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    request: AgentQueryRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query a specific agent or let the system choose

    Args:
        request: Agent query with optional agent selection
        db: Database session
        current_user: Authenticated user

    Returns:
        Agent response with metadata
    """
    try:
        # Use multi-agent service
        result = await multi_agent_service.process_query(
            query=request.query,
            agent_type=request.agent_type,
            chat_history=request.chat_history or [],
            user_language=request.language or 'pt',
            db=db
        )

        return AgentQueryResponse(
            success=result.get('success', True),
            query=request.query,
            response=result.get('response', ''),
            agent_used=result.get('agent_used', 'unknown'),
            reasoning=result.get('reasoning'),
            confidence_score=result.get('confidence_score'),
            llm_provider=result.get('llm_provider'),
            response_time_ms=result.get('response_time_ms', 0),
            metadata=result.get('metadata', {})
        )

    except Exception as e:
        logger.error(f"Agent query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    List available agents and their capabilities

    Returns:
        List of available agents with descriptions
    """
    try:
        agents = [
            AgentInfo(
                name="knight",
                display_name="Knight Agent",
                description="Expert em documentação corporativa e processos internos",
                capabilities=[
                    "Responder perguntas sobre políticas da empresa",
                    "Explicar processos e procedimentos",
                    "Orientar sobre recursos disponíveis"
                ],
                languages=["pt", "en", "es"],
                is_default=True
            ),
            AgentInfo(
                name="bard",
                display_name="Bard Agent",
                description="Especialista em análise e síntese de informações",
                capabilities=[
                    "Analisar documentos complexos",
                    "Criar resumos executivos",
                    "Comparar e contrastar informações"
                ],
                languages=["pt", "en", "es"],
                is_default=False
            ),
            AgentInfo(
                name="wizard",
                display_name="Wizard Agent",
                description="Mestre em resolução de problemas técnicos",
                capabilities=[
                    "Diagnosticar problemas técnicos",
                    "Sugerir soluções passo a passo",
                    "Explicar conceitos técnicos"
                ],
                languages=["pt", "en", "es"],
                is_default=False
            )
        ]

        return AgentListResponse(
            agents=agents,
            total=len(agents)
        )

    except Exception as e:
        logger.error(f"List agents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_agent_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get multi-agent system statistics

    Returns:
        Usage statistics for each agent
    """
    try:
        # TODO: Implement actual statistics from database
        return {
            "total_queries": 0,
            "agents": {
                "knight": {
                    "queries": 0,
                    "average_response_time": 0,
                    "success_rate": 1.0
                },
                "bard": {
                    "queries": 0,
                    "average_response_time": 0,
                    "success_rate": 1.0
                },
                "wizard": {
                    "queries": 0,
                    "average_response_time": 0,
                    "success_rate": 1.0
                }
            },
            "most_used_agent": "knight",
            "average_confidence": 0.85
        }

    except Exception as e:
        logger.error(f"Get agent stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/select")
async def select_best_agent(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Let the system select the best agent for a query

    Args:
        request: Query and context for agent selection

    Returns:
        Selected agent and reasoning
    """
    try:
        query = request.get('query', '')
        context = request.get('context', '')

        # Use multi-agent service to select best agent
        selected = await multi_agent_service.select_agent(query, context)

        return {
            "query": query,
            "selected_agent": selected.get('agent', 'knight'),
            "reasoning": selected.get('reasoning', ''),
            "confidence": selected.get('confidence', 0.8)
        }

    except Exception as e:
        logger.error(f"Agent selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))