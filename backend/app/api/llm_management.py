"""
LLM Provider Management API endpoints
Admin-only endpoints for managing LLM providers, metrics, and costs
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import logging

from app.api.deps import get_async_db, get_current_admin_user
from app.models.user import User
from app.models.rag import RAGQueryLog
from app.services.rag.llm_providers import llm_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag/llm", tags=["llm-management"])

# Provider costs (USD per 1k tokens)
PROVIDER_COSTS = {
    'cohere': {
        'command-r-plus': {'input': 0.003, 'output': 0.015},
        'command-r': {'input': 0.0015, 'output': 0.0075}
    },
    'groq': {
        'llama3-70b-8192': {'input': 0.00059, 'output': 0.00079},
        'mixtral-8x7b-32768': {'input': 0.00024, 'output': 0.00024}
    },
    'together': {
        'mixtral-8x7b': {'input': 0.0006, 'output': 0.0006},
        'llama3-70b': {'input': 0.0008, 'output': 0.0008}
    },
    'ollama': {
        'llama3.2': {'input': 0.0, 'output': 0.0},  # Free (local)
        'mistral': {'input': 0.0, 'output': 0.0}
    }
}

PROVIDER_INFO = {
    'cohere': {
        'name': 'Cohere',
        'color': '#39c5bb',
        'icon': '/cohere-logo.svg',
        'description': 'Optimized for RAG'
    },
    'groq': {
        'name': 'Groq',
        'color': '#f97316',
        'icon': '/groq-logo.svg',
        'description': 'Ultra-fast inference'
    },
    'together': {
        'name': 'Together AI',
        'color': '#6366f1',
        'icon': '/together-logo.svg',
        'description': 'Open source models'
    },
    'ollama': {
        'name': 'Ollama',
        'color': '#000000',
        'icon': '/ollama-logo.svg',
        'description': 'Local models, no cost'
    }
}


class LLMStatusResponse(BaseModel):
    """LLM provider status response"""
    current_provider: str
    is_available: bool
    health_status: dict
    response_time: float
    last_check: datetime


class LLMProviderInfo(BaseModel):
    """LLM provider information"""
    key: str
    name: str
    color: str
    icon: str
    description: str
    is_available: bool
    api_key_configured: bool
    is_current: bool


class LLMConfigUpdate(BaseModel):
    """LLM configuration update request"""
    provider: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status(
    admin_user: User = Depends(get_current_admin_user)
):
    """Get current LLM provider status"""
    try:
        current_provider = settings.LLM_PROVIDER

        # Test provider health
        health_status = await test_provider_health(current_provider)

        return LLMStatusResponse(
            current_provider=current_provider,
            is_available=current_provider in llm_manager.get_available_providers(),
            health_status=health_status,
            response_time=health_status.get('response_time', 0),
            last_check=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_provider(
    admin_user: User = Depends(get_current_admin_user)
):
    """Get current LLM provider configuration"""
    try:
        current_provider = settings.LLM_PROVIDER
        provider_info = PROVIDER_INFO.get(current_provider, {})

        return {
            'current_provider': current_provider,
            'provider_info': provider_info,
            'is_available': current_provider in llm_manager.get_available_providers(),
            'fallback_order': llm_manager.fallback_order,
            'last_check': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting current provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available")
async def get_available_providers(
    admin_user: User = Depends(get_current_admin_user)
):
    """Get all available LLM providers"""
    try:
        available_providers = llm_manager.get_available_providers()
        current_provider = settings.LLM_PROVIDER

        providers_status = []
        for provider_key, provider_info in PROVIDER_INFO.items():
            is_available = provider_key in available_providers
            api_key_configured = check_api_key(provider_key)

            providers_status.append({
                'key': provider_key,
                'name': provider_info['name'],
                'color': provider_info['color'],
                'icon': provider_info['icon'],
                'description': provider_info['description'],
                'is_available': is_available,
                'api_key_configured': api_key_configured,
                'is_current': provider_key == current_provider
            })

        return {
            'providers': providers_status,
            'total_available': len(available_providers),
            'current_provider': current_provider
        }
    except Exception as e:
        logger.error(f"Error getting available providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_llm_metrics(
    period: str = Query("month", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Get LLM usage metrics"""
    try:
        # Calculate date range
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:  # month
            start_date = now - timedelta(days=30)

        # Query metrics from RAGQueryLog
        query = select(
            func.count(RAGQueryLog.id).label('total_queries'),
            func.avg(RAGQueryLog.response_time).label('avg_response_time'),
            func.sum(RAGQueryLog.tokens_used).label('total_tokens')
        ).where(RAGQueryLog.created_at >= start_date)

        result = await db.execute(query)
        metrics = result.one()

        return {
            'period': period,
            'total_queries': metrics.total_queries or 0,
            'avg_response_time': float(metrics.avg_response_time or 0),
            'total_tokens': metrics.total_tokens or 0,
            'start_date': start_date.isoformat(),
            'end_date': now.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting LLM metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs")
async def get_llm_costs(
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Get LLM usage costs"""
    try:
        # Get token usage by provider
        query = select(
            RAGQueryLog.provider,
            func.sum(RAGQueryLog.tokens_used).label('total_tokens')
        ).group_by(RAGQueryLog.provider)

        result = await db.execute(query)
        usage = result.all()

        costs = []
        total_cost = 0.0

        for provider, tokens in usage:
            if provider and tokens:
                provider_cost = calculate_provider_cost(provider, tokens)
                costs.append({
                    'provider': provider,
                    'tokens': tokens,
                    'cost': provider_cost
                })
                total_cost += provider_cost

        return {
            'costs_by_provider': costs,
            'total_cost': total_cost,
            'currency': 'USD'
        }
    except Exception as e:
        logger.error(f"Error getting LLM costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_llm_history(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Get LLM query history"""
    try:
        query = select(RAGQueryLog).order_by(
            RAGQueryLog.created_at.desc()
        ).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        history = []
        for log in logs:
            history.append({
                'id': log.id,
                'query': log.query[:100] + '...' if len(log.query) > 100 else log.query,
                'provider': log.provider,
                'model': log.model,
                'response_time': log.response_time,
                'tokens_used': log.tokens_used,
                'success': log.success,
                'created_at': log.created_at.isoformat() if log.created_at else None
            })

        return {
            'history': history,
            'total': len(history)
        }
    except Exception as e:
        logger.error(f"Error getting LLM history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-config")
async def update_llm_config(
    config: LLMConfigUpdate,
    admin_user: User = Depends(get_current_admin_user)
):
    """Update LLM configuration"""
    try:

        # Validate provider
        if config.provider not in llm_manager.get_available_providers():
            raise HTTPException(
                status_code=400,
                detail=f"Provider {config.provider} is not available"
            )

        # Update configuration
        # Note: In production, you'd want to persist this to database or config file
        os.environ['LLM_PROVIDER'] = config.provider

        if config.temperature is not None:
            os.environ['LLM_TEMPERATURE'] = str(config.temperature)

        if config.max_tokens is not None:
            os.environ['LLM_MAX_TOKENS'] = str(config.max_tokens)

        return {
            'success': True,
            'message': f'LLM provider updated to {config.provider}',
            'new_provider': config.provider
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def test_provider_health(provider_name: str) -> dict:
    """Test LLM provider health"""
    try:
        start_time = datetime.now()

        # Simple health check
        result = llm_manager.generate_response(
            prompt="Test",
            provider=provider_name,
            max_tokens=10,
            temperature=0.1
        )

        response_time = (datetime.now() - start_time).total_seconds()

        return {
            'is_healthy': result.get('success', False),
            'response_time': response_time,
            'error': result.get('error') if not result.get('success') else None
        }
    except Exception as e:
        return {
            'is_healthy': False,
            'response_time': 0,
            'error': str(e)
        }


def check_api_key(provider_key: str) -> bool:
    """Check if API key is configured for provider"""
    key_mapping = {
        'cohere': 'COHERE_API_KEY',
        'groq': 'GROQ_API_KEY',
        'together': 'TOGETHER_API_KEY',
        'ollama': 'OLLAMA_BASE_URL'
    }

    env_key = key_mapping.get(provider_key)
    if not env_key:
        return False

    return bool(os.getenv(env_key))


def calculate_provider_cost(provider: str, tokens: int) -> float:
    """Calculate cost for provider token usage"""
    if provider not in PROVIDER_COSTS:
        return 0.0

    # Simplified calculation - assuming equal input/output
    provider_rates = PROVIDER_COSTS.get(provider, {})
    if not provider_rates:
        return 0.0

    # Get first model rates as default
    model_rates = list(provider_rates.values())[0] if provider_rates else {'input': 0, 'output': 0}

    # Assume 50/50 input/output ratio
    input_cost = (tokens * 0.5 / 1000) * model_rates.get('input', 0)
    output_cost = (tokens * 0.5 / 1000) * model_rates.get('output', 0)

    return input_cost + output_cost