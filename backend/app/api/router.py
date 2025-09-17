"""
Main API router for v1 endpoints
Consolidates all API routes
"""
from fastapi import APIRouter

from app.api import auth, rag, documents, chat, downloads, knowledge, locales, agents

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth.router)
api_router.include_router(rag.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(agents.router)
api_router.include_router(downloads.router)
api_router.include_router(knowledge.router)
api_router.include_router(locales.router)