"""
Knight Agent FastAPI Application
Migrated from Django REST Framework
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

# Import app modules
from app.core.config import settings
from app.core.middleware import setup_middlewares
from app.core.database import init_database, close_database, check_database_connection
from app.api.router import api_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia startup e shutdown events
    """
    # Startup
    logger.info("🚀 Knight Agent FastAPI starting up...")

    # Initialize database
    try:
        await init_database()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")

    yield

    # Shutdown
    logger.info("👋 Knight Agent FastAPI shutting down...")
    await close_database()

# Criar instância FastAPI
app = FastAPI(
    title="Knight Agent API",
    description="""
    ## 🛡️ Knight Agent - Corporate AI Assistant

    **Advanced RAG system with multi-agent architecture**

    ### Features:
    - 🤖 **Agentic RAG**: LangGraph-based multi-step reasoning
    - 🔍 **Hybrid Search**: pgvector + BM25 optimized for Portuguese
    - 🎯 **Multi-Agent System**: Knight (supervisor), Bard (reports), Wizard (training)
    - 🔐 **Azure AD Authentication**: Enterprise-grade security
    - 📄 **Document Processing**: Async processing with Docling
    - 💬 **Real-time Chat**: WebSocket support for streaming responses
    - 🌍 **i18n Support**: Multi-language interface (PT, EN, ES)
    - 📦 **Knowledge Resources**: Contextual link and document suggestions

    ### API Version: 2.0.0
    Migrated from Django to FastAPI for improved performance and scalability.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    terms_of_service="https://knight-agent.com/terms",
    contact={
        "name": "Knight Agent Support",
        "url": "https://knight-agent.com",
        "email": "support@knight-agent.com"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://knight-agent.com/license"
    }
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://knight-frontend-dev.loca.lt",
    ],
    allow_credentials=False,  # Mantendo configuração de segurança do Django
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
    ],
)

# Adicionar compressão Gzip
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup custom middlewares
setup_middlewares(app)

# Add rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api.deps import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Servir arquivos estáticos (se existirem)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

media_path = Path(__file__).parent.parent / "media"
if media_path.exists():
    app.mount("/media", StaticFiles(directory=str(media_path)), name="media")

# Rotas básicas de health check
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Knight Agent API",
        "version": "2.0.0",
        "status": "running",
        "framework": "FastAPI"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check database connection
    db_status = await check_database_connection()

    health_status = {
        "status": "healthy" if db_status else "degraded",
        "api": "operational",
        "database": "operational" if db_status else "error",
        "background_tasks": "operational",  # FastAPI background tasks sempre disponíveis
        "cache": "pending"     # TODO: Implementar check real (Redis se necessário)
    }
    return health_status

@app.get("/api/ping")
async def ping():
    """Simple ping endpoint for testing"""
    return {"ping": "pong"}

# Incluir routers dos módulos
app.include_router(api_router, prefix="/api")

# Tratamento de erros customizado
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

# Metadata da API
app.openapi_tags = [
    {
        "name": "auth",
        "description": "Authentication and authorization operations",
        "externalDocs": {
            "description": "Azure AD Authentication",
            "url": "https://docs.microsoft.com/azure/active-directory/develop/"
        }
    },
    {
        "name": "documents",
        "description": "Document upload, processing and management",
    },
    {
        "name": "rag",
        "description": "Retrieval-Augmented Generation and search operations",
        "externalDocs": {
            "description": "LangGraph Documentation",
            "url": "https://python.langchain.com/docs/langgraph"
        }
    },
    {
        "name": "chat",
        "description": "Chat interface with WebSocket support",
    },
    {
        "name": "downloads",
        "description": "Temporary file distribution with expiration",
    },
    {
        "name": "knowledge",
        "description": "Knowledge resources - links and documents",
    },
    {
        "name": "locales",
        "description": "Internationalization and translation management",
    },
    {
        "name": "websocket",
        "description": "WebSocket endpoints for real-time communication",
    },
]

# WebSocket connection manager
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_message(self, message: str, session_id: int):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        for session_connections in self.active_connections.values():
            for connection in session_connections:
                await connection.send_text(message)

# Create global connection manager
manager = ConnectionManager()

# WebSocket endpoint for system monitoring
@app.websocket("/ws/system")
async def system_websocket(websocket: WebSocket):
    """System monitoring WebSocket for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic health status
            import asyncio
            health = await health_check()
            await websocket.send_json(health)
            await asyncio.sleep(5)  # Update every 5 seconds
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )