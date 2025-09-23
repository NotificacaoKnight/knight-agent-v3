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
from app.services.rag.llm_providers import llm_manager, ProviderType
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag/llm", tags=["llm-management"])

# Provider costs (USD per 1k tokens)
PROVIDER_COSTS = {
    'deepseek': {
        'deepseek-chat': {'input': 0.00014, 'output': 0.00028}
    },
    'gemini': {
        'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003}
    },
    'openai': {
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006}
    },
    'cohere': {
        'command-r-plus': {'input': 0.003, 'output': 0.015},
        'command-r': {'input': 0.0015, 'output': 0.0075}
    },
    'groq': {
        'llama3-70b-8192': {'input': 0.00059, 'output': 0.00079},
        'mixtral-8x7b-32768': {'input': 0.00024, 'output': 0.00024}
    }
}

PROVIDER_INFO = {
    'deepseek': {
        'name': 'DeepSeek',
        'color': '#1e40af',
        'icon': '/deepseek-logo.svg',
        'description': 'Cost-effective AI model'
    },
    'gemini': {
        'name': 'Google Gemini',
        'color': '#4285f4',
        'icon': '/google-gemini-logo.svg',
        'description': 'Google\'s multimodal AI'
    },
    'openai': {
        'name': 'OpenAI',
        'color': '#10a37f',
        'icon': '/openai-logo.svg',
        'description': 'Advanced language models'
    },
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


class SwitchProviderRequest(BaseModel):
    """LLM provider switch request"""
    provider: str
    test_connection: bool = True
    reason: str = "Switch via admin interface"


@router.get("/status")
async def get_llm_status(
    admin_user: User = Depends(get_current_admin_user)
):
    """Get current LLM provider status"""
    try:
        current_provider = settings.LLM_PROVIDER
        provider_info = PROVIDER_INFO.get(current_provider, {})

        # Use simple availability check instead of expensive health test
        # Health testing should only be done on demand (switch, test endpoints)
        is_available = any(
            p.get('type') == current_provider and p.get('available', False)
            for p in llm_manager.get_available_providers()
        )

        # Assume healthy if available and API key configured
        api_key_configured = check_api_key(current_provider)
        is_healthy = is_available and api_key_configured

        return {
            "current_provider": current_provider,
            "provider_name": provider_info.get('name', current_provider.title()),
            "is_healthy": is_healthy,
            "status": "operational" if is_healthy else "error",
            "is_available": is_available,
            "health_status": {"is_healthy": is_healthy, "response_time": 0, "error": None},
            "response_time": 0,
            "last_check": datetime.now().isoformat()
        }
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
            'is_available': any(
                p.get('type') == current_provider and p.get('available', False)
                for p in llm_manager.get_available_providers()
            ),
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

        logger.info(f"Available providers from llm_manager: {available_providers}")
        logger.info(f"Current provider: {current_provider}")

        providers_status = []
        for provider_key, provider_info in PROVIDER_INFO.items():
            # Corrigir verificação: procurar na lista de dicts retornada por get_available_providers()
            is_available = any(
                p.get('type') == provider_key and p.get('available', False)
                for p in available_providers
            )
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
    """Get comprehensive LLM usage metrics"""
    try:
        # Calculate date range
        now = datetime.now()
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "week":
            start_date = now - timedelta(weeks=1)
        else:  # month
            start_date = now - timedelta(days=30)

        # Mock data for development - will be replaced with real queries
        # Note: In production, this would come from RAGQueryLog table
        total_queries = 150
        successful_queries = 145
        avg_response_time = 1250.5  # in ms

        # Mock provider metrics
        by_provider = [
            {
                'provider': 'deepseek',
                'count': 90,
                'avg_time': 1200,
                'total_input': 45000,
                'total_output': 35000
            },
            {
                'provider': 'gemini',
                'count': 60,
                'avg_time': 1300,
                'total_input': 30000,
                'total_output': 25000
            }
        ]

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': now.isoformat()
            },
            'summary': {
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'success_rate': round((successful_queries / total_queries * 100) if total_queries > 0 else 0, 1),
                'avg_response_time_ms': avg_response_time,
                'total_input_tokens': 75000,
                'total_output_tokens': 60000,
                'total_tokens': 135000,
                'estimated_cost_usd': 5.67
            },
            'by_provider': by_provider
        }
    except Exception as e:
        logger.error(f"Error getting LLM metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs")
async def get_llm_costs(
    db: AsyncSession = Depends(get_async_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """Get LLM usage costs with period analysis"""
    try:
        # Base daily cost for mock data (will be replaced with real calculations)
        base_daily_cost = 2.35

        # Calculate costs for different periods
        cost_analysis = {
            'month': {
                'period': 'month',
                'total_cost_usd': round(base_daily_cost * 30, 2),
                'daily_average': base_daily_cost,
                'breakdown': {
                    'input_tokens_cost': round(base_daily_cost * 30 * 0.4, 2),
                    'output_tokens_cost': round(base_daily_cost * 30 * 0.6, 2)
                }
            },
            '6months': {
                'period': '6months',
                'total_cost_usd': round(base_daily_cost * 180 * 0.95, 2),  # 5% discount
                'daily_average': round(base_daily_cost * 0.95, 2),
                'breakdown': {
                    'input_tokens_cost': round(base_daily_cost * 180 * 0.95 * 0.4, 2),
                    'output_tokens_cost': round(base_daily_cost * 180 * 0.95 * 0.6, 2)
                }
            },
            'year': {
                'period': 'year',
                'total_cost_usd': round(base_daily_cost * 365 * 0.90, 2),  # 10% discount
                'daily_average': round(base_daily_cost * 0.90, 2),
                'breakdown': {
                    'input_tokens_cost': round(base_daily_cost * 365 * 0.90 * 0.4, 2),
                    'output_tokens_cost': round(base_daily_cost * 365 * 0.90 * 0.6, 2)
                }
            }
        }

        # Projections based on usage trends
        projections = {
            'next_month': round(base_daily_cost * 30 * 1.1, 2),  # 10% growth
            'next_quarter': round(base_daily_cost * 90 * 1.15, 2),  # 15% growth
            'next_year': round(base_daily_cost * 365 * 1.3, 2),  # 30% growth
            'confidence': 'Média',
            'factors': [
                'Baseado em uso histórico',
                'Tendência de crescimento de 10% ao mês',
                'Possível aumento de usuários'
            ]
        }

        # Provider comparison
        provider_comparison = [
            {
                'provider': 'deepseek',
                'name': 'DeepSeek',
                'model': 'deepseek-chat',
                'monthly_cost_usd': base_daily_cost * 30,
                'input_cost_per_1k': 0.00014,
                'output_cost_per_1k': 0.00028,
                'estimated_savings': 0
            },
            {
                'provider': 'gemini',
                'name': 'Google Gemini',
                'model': 'gemini-1.5-flash',
                'monthly_cost_usd': base_daily_cost * 30 * 0.8,
                'input_cost_per_1k': 0.000075,
                'output_cost_per_1k': 0.0003,
                'estimated_savings': base_daily_cost * 30 * 0.2
            }
        ]

        return {
            'costs_by_period': cost_analysis,
            'projections': projections,
            'provider_comparison': provider_comparison,
            'generated_at': datetime.now().isoformat()
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
    """Get LLM provider change history"""
    try:
        # Mock data for provider change history - in production would come from a dedicated table
        # This represents changes in LLM provider selection, not query history
        history_entries = [
            {
                'timestamp': (datetime.now() - timedelta(days=2)).isoformat(),
                'user': 'felipe.nascimento@semcon.com',
                'old_provider': 'groq',
                'new_provider': 'deepseek',
                'reason': 'Melhor custo-benefício',
                'provider_names': {
                    'old': 'Groq',
                    'new': 'DeepSeek'
                }
            },
            {
                'timestamp': (datetime.now() - timedelta(days=7)).isoformat(),
                'user': 'paulo.pereira@semcon.com',
                'old_provider': 'cohere',
                'new_provider': 'groq',
                'reason': 'Teste de performance',
                'provider_names': {
                    'old': 'Cohere',
                    'new': 'Groq'
                }
            },
            {
                'timestamp': (datetime.now() - timedelta(days=15)).isoformat(),
                'user': 'felipe.nascimento@semcon.com',
                'old_provider': 'gemini',
                'new_provider': 'cohere',
                'reason': 'Melhor qualidade para RAG',
                'provider_names': {
                    'old': 'Google Gemini',
                    'new': 'Cohere'
                }
            }
        ]

        return {
            'history': history_entries[:limit],
            'total': len(history_entries)
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
        # Verificar se provider está disponível
        available_providers = llm_manager.get_available_providers()
        provider_available = any(
            p.get('type') == config.provider and p.get('available', False)
            for p in available_providers
        )
        if not provider_available:
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


@router.post("/switch")
async def switch_provider(
    request: SwitchProviderRequest,
    admin_user: User = Depends(get_current_admin_user)
):
    """Switch LLM provider with validation and testing"""
    try:
        new_provider = request.provider
        test_connection = request.test_connection
        reason = request.reason

        # Validate provider exists
        if new_provider not in PROVIDER_INFO:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {new_provider} is not valid"
            )

        # Get current provider
        current_provider = settings.LLM_PROVIDER

        # Check if already current provider
        if current_provider == new_provider:
            return {
                "success": True,
                "message": f"{PROVIDER_INFO[new_provider]['name']} is already the active provider",
                "old_provider": current_provider,
                "new_provider": new_provider,
                "restart_required": False
            }

        # Check if provider is available (has API key configured)
        if not check_api_key(new_provider):
            raise HTTPException(
                status_code=400,
                detail=f"Provider {new_provider} is not configured (missing API key)"
            )

        # Test connection if requested
        if test_connection:
            health_status = await test_provider_health(new_provider)
            if not health_status.get('is_healthy', False):
                raise HTTPException(
                    status_code=400,
                    detail=f"Connection test failed for {new_provider}: {health_status.get('error', 'Unknown error')}"
                )

        # Update configuration
        os.environ['LLM_PROVIDER'] = new_provider
        settings.LLM_PROVIDER = new_provider  # Update settings object directly

        # Log the change
        logger.info(f"LLM provider switched from {current_provider} to {new_provider} by {admin_user.email}. Reason: {reason}")

        return {
            "success": True,
            "message": f"Provider switched to {PROVIDER_INFO[new_provider]['name']} successfully",
            "old_provider": current_provider,
            "new_provider": new_provider,
            "restart_required": False,  # FastAPI with reload handles this automatically
            "test_connection": test_connection,
            "reason": reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching LLM provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def test_provider_health(provider_name: str) -> dict:
    """Test LLM provider health"""
    try:
        start_time = datetime.now()

        # Test specific provider directly, not using fallback
        provider = llm_manager.get_provider(ProviderType(provider_name))
        provider.initialize()

        # Simple health check
        result = await provider.generate(
            prompt="Test",
            max_tokens=10,
            temperature=0.1
        )

        response_time = (datetime.now() - start_time).total_seconds()

        # If we got here without exception, provider is healthy
        is_healthy = bool(result)

        return {
            'is_healthy': is_healthy,
            'response_time': response_time,
            'error': None
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
        'deepseek': settings.DEEPSEEK_API_KEY,
        'gemini': settings.GEMINI_API_KEY,
        'openai': settings.OPENAI_API_KEY,
        'cohere': settings.COHERE_API_KEY,
        'groq': settings.GROQ_API_KEY
    }

    api_key = key_mapping.get(provider_key)
    return bool(api_key)


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