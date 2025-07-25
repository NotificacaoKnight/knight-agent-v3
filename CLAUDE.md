# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Knight Agent is a corporate AI assistant system built for internal company support, featuring hybrid RAG (Retrieval-Augmented Generation) optimized for Portuguese documents. The system supports multiple LLM providers with automatic fallback and includes Microsoft Azure AD authentication.

## Architecture

The project uses a **microservices-style Django architecture** with separate apps for distinct functionalities:

- **authentication/**: Microsoft Azure AD integration with MSAL
- **documents/**: Document processing pipeline using Docling + async Celery tasks
- **rag/**: Hybrid search engine (FAISS vector store + BM25) with multiple LLM provider abstraction
- **chat/**: Conversational interface with session management
- **downloads/**: Temporary file distribution system (7-day expiry)

**Key architectural patterns:**
- **Provider Pattern**: `rag/llm_providers.py` abstracts multiple LLM APIs (Cohere, Groq, Together AI, Ollama) with automatic fallback
- **Hybrid Search**: Combines semantic search (BGE-m3 embeddings) with keyword search (BM25) for Portuguese optimization
- **Async Processing**: Document ingestion uses Celery for background processing (chunking, embedding generation, indexing)
- **Token Authentication**: Custom middleware (`authentication/middleware.py`) for session token management

## Project Structure

```
knight-agent/
├── backend/                    # Django REST API
│   ├── knight_backend/         # Main Django settings
│   ├── authentication/         # Microsoft Azure AD
│   ├── documents/              # Document processing pipeline
│   ├── rag/                    # Hybrid search engine
│   ├── chat/                   # Chat interface
│   ├── downloads/              # Temporary file distribution
│   ├── manage.py               # Django management
│   ├── requirements.txt        # Python dependencies
│   └── *.py                    # Utility scripts (create_migrations, reset_database, etc.)
├── frontend/                   # React TypeScript app
│   ├── src/                    # React source code
│   ├── public/                 # Static assets
│   └── package.json           # Node.js dependencies
├── setup.sh / setup.bat       # Initial setup scripts
└── docker-compose.yml         # Development environment
```

## Development Commands

### Quick Start

```bash
# Initial setup scripts
./setup.sh         # Linux/Mac
setup.bat          # Windows

# Or manual setup:
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Backend (Django)

**Working Directory**: All Django commands must be run from `/backend/` directory.

```bash
cd backend  # IMPORTANT: Always run from backend directory

# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Create all app migrations at once
python create_migrations.py


# Fix migration issues
./fix_migrations.sh  # Linux/Mac
fix_migrations.bat   # Windows

# Run development server
python manage.py runserver

# Start Celery worker (required for document processing)
celery -A knight_backend worker -l info

# Start Celery beat (for scheduled tasks)
celery -A knight_backend beat -l info

# Run tests
pytest
pytest path/to/specific_test.py::TestClass::test_method

# Code formatting and linting
black .
flake8 .

# Django shell for debugging
python manage.py shell
```

### Frontend (React/TypeScript)

```bash
cd frontend
npm install
npm start  # Development server on port 3000
npm run build  # Production build
npm test  # Run tests
```

**Note**: Frontend uses React Scripts (Create React App), not Next.js as mentioned in README.md. Key packages: MSAL React, TanStack Query, Axios, Tailwind CSS.

### Linting and Code Quality

**Backend (Django):**
```bash
cd backend
black .
flake8 .
```

**Frontend (React/TypeScript):**
```bash
cd frontend
npm run lint  # ESLint with TypeScript rules
npm run lint:fix  # Auto-fix linting issues
```

### Testing Authentication

```bash
# Test authenticated endpoints
curl -X GET http://localhost:8000/api/auth/me/ -H "Authorization: Bearer YOUR_TOKEN"
```

### Docker Development

```bash
# Full stack with PostgreSQL and Redis
docker-compose up -d

# Backend only
docker-compose up backend postgres redis

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Rebuild after code changes
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

## Configuration Requirements

### Essential Environment Variables (.env)

**Microsoft Azure AD (Required):**
```env
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
```

**LLM Provider (Choose one):**
```env
# Cohere (recommended for production RAG)
LLM_PROVIDER=cohere
COHERE_API_KEY=your-api-key

# Groq (fastest inference)
LLM_PROVIDER=groq
GROQ_API_KEY=your-api-key

# Ollama (self-hosted, no API costs)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**RAG Configuration (Pre-optimized for Portuguese):**
```env
EMBEDDING_MODEL=BAAI/bge-m3
CHUNK_SIZE=700
CHUNK_OVERLAP=100
BM25_WEIGHT=0.3
SEMANTIC_WEIGHT=0.7
```

## Core Systems Understanding

### Authentication System

1. **Authentication**:
   - Microsoft Azure AD via MSAL

2. **Token Management**:
   - Frontend stores session token in localStorage
   - `api.ts` service automatically includes Bearer token in requests
   - `TokenAuthenticationMiddleware` validates tokens on each request
   - Sessions expire after 1 hour

3. **Key Files**:
   - `backend/authentication/views.py`: Login endpoints
   - `backend/authentication/middleware.py`: Token validation middleware
   - `frontend/src/context/AuthContext.tsx`: React authentication state management
   - `frontend/src/services/api.ts`: Axios instance with auth interceptors

### RAG Hybrid Search Flow

1. **Document Ingestion** (`documents/tasks.py`):
   - Docling converts documents to markdown
   - Text is chunked preserving structure (headers, paragraphs)
   - BGE-m3 embeddings generated for each chunk
   - FAISS index updated, BM25 corpus rebuilt

2. **Query Processing** (`rag/services.py`):
   - Parallel search: FAISS semantic + BM25 keyword
   - Score normalization and weighted combination
   - Results passed to LLM provider with context

3. **LLM Response** (`rag/llm_providers.py`):
   - Provider selection with automatic fallback
   - Context injection with Portuguese-optimized prompts
   - Structured response with citations (Cohere) or basic text

### Document Processing Pipeline

- Upload → Celery task → Docling conversion → Chunking → Embedding → Indexing
- Status tracking through `ProcessingJob` model
- Error handling with retry logic

## Security Considerations

- CSRF temporarily disabled for API development (re-enable for production)
- CORS configured for localhost:3000 with credentials support
- Custom authentication backend bypasses some Django defaults

## Common Issues and Solutions

### 403 Forbidden on API calls

1. CSRF is disabled but check for other middleware conflicts
2. Ensure CORS headers are properly configured
3. Verify authentication token is being sent in requests

### Database errors (no such table)

1. Run `python create_migrations.py` to create all migrations
2. Then apply migrations: `python manage.py migrate`
3. For migration conflicts, use fix scripts: `./fix_migrations.sh` (Linux/Mac) or `fix_migrations.bat` (Windows)

## LLM Provider Switching

The system uses a provider abstraction that allows runtime switching between:
- **Agno**: Advanced multi-agent framework with high performance (agents initialize in ~3μs)
- **Cohere**: Best for RAG with native document support
- **Groq**: Fastest inference (<500ms)
- **Together AI**: Open-source model variety
- **Ollama**: Self-hosted for data privacy
- **Gemini**: Google's powerful multimodal model

Change providers by updating `LLM_PROVIDER` environment variable. Fallback order is configurable in `rag/llm_providers.py`.

### Agno Provider Configuration

Agno is a powerful multi-agent framework that supports 23+ model providers. To use Agno:

```env
LLM_PROVIDER=agno
AGNO_MODEL_PROVIDER=openai  # or cohere, groq, etc
AGNO_MODEL_NAME=gpt-4o-mini
```

Agno provides:
- Native multi-modal support (text, image, audio, video)
- Built-in memory and session storage
- Advanced reasoning capabilities
- Agentic RAG with async performance
- Support for multiple vector databases
- Audio transcription via Gemini (no OpenAI Whisper needed)

## Portuguese Optimization

- **Chunking**: 500-800 tokens optimized for Portuguese text structure
- **Embeddings**: BGE-m3 multilingual model with Portuguese training
- **BM25 Tokenization**: Custom Portuguese stopwords and tokenization
- **Prompts**: System prompts specifically designed for Brazilian Portuguese responses

## File Locations and Key Entry Points

### Backend Key Files
- `backend/knight_backend/settings.py`: Main Django configuration
- `backend/authentication/middleware.py`: Custom token authentication
- `backend/rag/llm_providers.py`: LLM provider abstraction layer
- `backend/rag/services.py`: Hybrid search implementation
- `backend/documents/tasks.py`: Celery async document processing
- `backend/create_migrations.py`: Utility to create migrations for all apps
- `backend/reset_database.py`: Development database reset utility

### Frontend Key Files
- `frontend/src/App.tsx`: Main React application entry point
- `frontend/src/context/AuthContext.tsx`: Global authentication state
- `frontend/src/services/api.ts`: Centralized API client with auth interceptors
- `frontend/src/pages/LoginPage.tsx`: Microsoft Azure AD login interface
- `frontend/tailwind.config.js`: Custom knight-* color scheme configuration

### Configuration Files
- `docker-compose.yml`: Development environment with PostgreSQL, Redis, Celery
- `setup.sh` / `setup.bat`: Initial project setup scripts
- `backend/.env`: Environment variables (copy from .env.example)

## Monitoring and Debugging

```bash
# View processing queue
docker-compose exec redis redis-cli
> KEYS celery*

# Check embedding generation
python manage.py shell
>>> from rag.services import EmbeddingService
>>> service = EmbeddingService()
>>> embeddings = service.encode_texts(["test text"])

# Monitor database queries
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)

# Vector store debugging
python manage.py shell
>>> from rag.services import VectorSearchService
>>> search = VectorSearchService()
>>> results = search.search("test query")

# Test authentication flow
python manage.py shell
>>> from authentication.models import User, UserSession
>>> User.objects.all()
>>> UserSession.objects.filter(is_active=True)
```

## Frontend Architecture

- **React 18** with TypeScript (Create React App)
- **MSAL React** for Microsoft Azure AD authentication
- **TanStack React Query** for server state management
- **Tailwind CSS** for styling with custom knight-* color scheme
- **Context API** for global state (Auth, Theme)
- **React Router** for navigation with protected routes
- **Axios** for API calls with automatic token injection
- **Lucide Icons** for consistent iconography
- **React Hot Toast** for notifications
- **React Markdown** for rendering formatted responses

## API Structure

All API endpoints are prefixed with `/api/`:
- `/api/auth/*` - Authentication endpoints
- `/api/documents/*` - Document upload and management
- `/api/rag/*` - RAG search functionality
- `/api/chat/*` - Chat interface endpoints
- `/api/downloads/*` - Temporary file downloads

## Testing Document Processing

```bash
# Test document upload and processing
curl -X POST http://localhost:8000/api/documents/upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "title=Test Document"

# Check processing status
curl http://localhost:8000/api/documents/stats/

# Test RAG search
curl -X POST http://localhost:8000/api/rag/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 5}'
```

## Important Development Patterns

### Working with the Codebase

1. **Always run Django commands from `/backend/` directory**: The Django project root is in the backend folder, not the repository root.

2. **Database Migration Workflow**:
   ```bash
   cd backend
   python create_migrations.py  # Creates migrations for all apps
   python manage.py migrate     # Applies migrations
   ```

3. **When making model changes**: Always run migrations after modifying models in any app (authentication, documents, rag, chat, downloads).

4. **Full Development Environment**:
   ```bash
   # Terminal 1: Django server
   cd backend && python manage.py runserver
   
   # Terminal 2: Celery worker (for document processing)
   cd backend && celery -A knight_backend worker -l info
   
   # Terminal 3: Frontend development server
   cd frontend && npm start
   
   # Terminal 4: Redis (if not using Docker)
   redis-server
   ```

5. **Environment Variables**: Always check `backend/.env` exists with required variables before debugging authentication or LLM issues.

### Troubleshooting Common Issues

**"No module named 'X'" errors**: Ensure you're in the correct directory and virtual environment is activated.

**Celery tasks not processing**: Check Redis is running and Celery worker is started with correct app name.

**Authentication token errors**: Verify middleware order in `settings.py` and check `TokenAuthenticationMiddleware` is properly configured.

**CORS errors**: Check `CORS_ALLOWED_ORIGINS` in settings and ensure frontend is running on expected port.

**Missing migrations**: Use `python create_migrations.py` instead of individual `makemigrations` commands.

**LLM provider errors**: Check API keys are set and provider is correctly specified in environment variables.

### Code Style Guidelines

- **Django**: Follow Django conventions, use class-based views for complex logic
- **React**: Use functional components with hooks, TypeScript strict mode enabled
- **API Design**: All endpoints use `/api/` prefix, consistent naming with Django REST Framework
- **Error Handling**: Always include proper error responses and logging
- **Authentication**: Use custom middleware for token validation, not Django's default auth

## LocalTunnel for Testing and External Access

### Tunnel Scripts

The project includes scripts for exposing the application via localtunnel for external testing:

```bash
# Quick tunnel setup (if services are already running)
./setup-tunnel.sh

# Complete development environment with tunnel
./start-dev-tunnel.sh

# Restart frontend with tunnel-specific configurations
./restart-frontend.sh
```

### Fixed URLs for Consistent Testing

The tunnel system uses **fixed subdomains** to avoid constant Azure AD configuration changes:

- **Frontend**: `https://knight-frontend-dev.loca.lt`
- **Backend**: `https://knight-backend-dev.loca.lt`

### Azure AD Configuration for Tunnel

**Required Azure AD settings** (see `AZURE_AD_SETUP.md` for details):

```
Redirect URIs:
- https://knight-frontend-dev.loca.lt
- http://localhost:3000

Front-channel logout URLs:
- Leave empty (prevents white screen after logout)
```

### Frontend Configuration for Tunnel

The frontend automatically detects tunnel usage via environment variables:

```env
# frontend/.env
REACT_APP_API_URL=https://knight-backend-dev.loca.lt  # For tunnel
DANGEROUSLY_DISABLE_HOST_CHECK=true  # Required for tunnel access
```

### Tunnel-Specific Commands

```bash
# Start frontend for tunnel (with host check disabled)
cd frontend && npm run start:tunnel

# Update CORS settings for tunnel (run once)
cd backend && python update_tunnel_cors.py
```

### Testing Documentation

External testers should receive:
- `TESTING_GUIDE.md`: Complete testing instructions
- `AZURE_AD_SETUP.md`: Azure AD configuration guide
- Fixed tunnel URLs for consistent access