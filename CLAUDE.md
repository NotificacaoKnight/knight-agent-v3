# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Knight Agent is a corporate AI assistant system built for internal company support, featuring **agentic RAG (Retrieval-Augmented Generation)** with LangGraph for multi-step reasoning, optimized for Portuguese documents. The system includes traditional hybrid search fallback, supports multiple LLM providers with automatic fallback, and includes Microsoft Azure AD authentication.

**Recent Migration**: The system has been migrated from traditional LangChain RAG to LangGraph-based agentic RAG, providing dynamic decision-making, self-reflection, and adaptive workflows while maintaining full backward compatibility.

## Architecture

The project uses a **microservices-style Django architecture** with separate apps for distinct functionalities:

- **authentication/**: Microsoft Azure AD integration with MSAL
- **documents/**: Document processing pipeline using Docling + async Celery tasks
- **rag/**: **Agentic RAG system** using LangGraph with traditional hybrid search fallback
- **chat/**: Conversational interface with session management
- **downloads/**: Temporary file distribution system (7-day expiry)

**Key architectural patterns:**
- **Agentic RAG**: `rag/agentic_rag_service.py` implements LangGraph-based multi-step reasoning with self-reflection, planning, and dynamic decision-making
- **Provider Pattern**: `rag/llm_providers.py` abstracts multiple LLM APIs (Cohere, Groq, Together AI, Ollama) with automatic fallback
- **Hybrid Search Fallback**: Traditional semantic search (BGE-m3 embeddings) + keyword search (BM25) for Portuguese optimization
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

**Note**: Frontend uses React Scripts (Create React App), not Next.js as mentioned in README.md. Key packages: MSAL React, TanStack Query, Axios, Tailwind CSS, shadcn/ui components.

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

# Agentic RAG Configuration (optional)
AGENTIC_RAG_MAX_SEARCH_ATTEMPTS=3
AGENTIC_RAG_QUALITY_THRESHOLD=0.6
AGENTIC_RAG_MAX_CONTEXT_LENGTH=8000
AGENTIC_RAG_MAX_TOKENS=1000
AGENTIC_RAG_TEMPERATURE=0.7
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

### Agentic RAG System Flow

**Primary System** (LangGraph-based):

1. **Planning Node** (`rag/agentic_rag_service.py`):
   - Analyzes query complexity and creates research plan
   - Determines multi-step reasoning strategy

2. **Search Node**:
   - Executes hybrid search (FAISS semantic + BM25 keyword)
   - Handles search failures with automatic retry
   - Combines results with configurable weights

3. **Quality Check Node**:
   - Evaluates search quality using multiple metrics
   - Routes to query refinement if quality is below threshold
   - Determines if additional context management is needed

4. **Query Refinement Node** (conditional):
   - Uses LLM to refine queries based on poor results
   - Implements iterative improvement with max attempts limit

5. **Context Management Node**:
   - Selects most relevant documents within token limits
   - Truncates context intelligently preserving key information
   - Creates summary for large document sets

6. **Generation Node**:
   - Generates response using configured LLM provider
   - Includes context from retrieved documents
   - Handles generation failures gracefully

7. **Validation Node**:
   - Assesses response quality against thresholds
   - Can trigger regeneration or context refinement
   - Ensures minimum response standards

**Fallback System** (Traditional Hybrid Search):
- Automatic fallback to `rag/services.py` hybrid search if agentic system fails
- Maintains backward compatibility with existing API structure

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

## Agentic RAG System (LangGraph)

### Core Components

**State Graph Architecture**: The agentic system uses LangGraph to model complex, multi-step reasoning as a state machine with conditional routing.

**Key Nodes**:
1. **Planner** - Analyzes query complexity and creates research plan
2. **Searcher** - Executes hybrid search with error handling
3. **Quality Checker** - Evaluates results and determines next action
4. **Query Refiner** - Refines queries using LLM when quality is low
5. **Context Manager** - Optimizes document selection within token limits
6. **Generator** - Creates final response using selected LLM provider
7. **Validator** - Assesses response quality and triggers refinement if needed
8. **Finalizer** - Prepares final output with metadata

**Conditional Routing**: Based on quality scores, the system can:
- Refine queries iteratively (up to max attempts)
- Adjust context management strategy
- Trigger regeneration for low-quality responses
- Fallback to traditional search if agentic system fails

### Configuration Management

**Environment-based Configuration** (`rag/agentic_config.py`):
- Development vs Production optimizations
- Configurable thresholds and timeouts
- Quality evaluation weights
- Search attempt limits

**Quality Metrics**:
- Search quality based on result relevance and count
- Response quality using length, context usage, and relevance
- Process-level evaluation for continuous improvement

### Migration Strategy

**Backward Compatibility**:
- Primary endpoint `/api/rag/search/` uses agentic with automatic fallback
- Flag `use_agentic=false` forces traditional hybrid search
- Dedicated `/api/rag/agentic/` endpoint for pure agentic mode
- All existing API response formats maintained

## LLM Provider Switching

The system uses a provider abstraction that allows runtime switching between:
- **Cohere**: Best for RAG with native document support
- **Groq**: Fastest inference (<500ms)
- **Together AI**: Open-source model variety
- **Ollama**: Self-hosted for data privacy

Change providers by updating `LLM_PROVIDER` environment variable. Fallback order is configurable in `rag/llm_providers.py`.

## Portuguese Optimization

- **Chunking**: 500-800 tokens optimized for Portuguese text structure
- **Embeddings**: BGE-m3 multilingual model with Portuguese training
- **BM25 Tokenization**: Custom Portuguese stopwords and tokenization
- **Prompts**: System prompts specifically designed for Brazilian Portuguese responses

## File Locations and Key Entry Points

### Backend Key Files
- `backend/knight_backend/settings.py`: Main Django configuration
- `backend/authentication/middleware.py`: Custom token authentication
- `backend/rag/agentic_rag_service.py`: **LangGraph-based agentic RAG system**
- `backend/rag/agentic_config.py`: **Centralized configuration for agentic parameters**
- `backend/rag/llm_providers.py`: LLM provider abstraction layer
- `backend/rag/services.py`: Traditional hybrid search implementation (fallback)
- `backend/rag/views.py`: RAG API endpoints with agentic/fallback routing
- `backend/documents/tasks.py`: Celery async document processing
- `backend/create_migrations.py`: Utility to create migrations for all apps
- `backend/reset_database.py`: Development database reset utility

### Frontend Key Files
- `frontend/src/App.tsx`: Main React application entry point
- `frontend/src/context/AuthContext.tsx`: Global authentication state
- `frontend/src/services/api.ts`: Centralized API client with auth interceptors
- `frontend/src/pages/LoginPage.tsx`: Microsoft Azure AD login interface
- `frontend/src/components/ui/`: shadcn/ui component library (Button, Card, Alert, Badge)
- `frontend/src/lib/utils.ts`: Utility functions for className merging (cn)
- `frontend/tailwind.config.js`: Custom knight-* color scheme with CSS variables and dark mode
- `frontend/postcss.config.js`: PostCSS configuration for Tailwind CSS

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

# Test agentic RAG system
python manage.py shell
>>> from rag.agentic_rag_service import AgenticRAGServiceSync
>>> agentic_service = AgenticRAGServiceSync()
>>> result = agentic_service.search("test query")
>>> print(result['quality_metrics'])

# Debug agentic configuration
python manage.py shell
>>> from rag.agentic_config import get_config
>>> config = get_config()
>>> print(config.get_search_config())
>>> print(config.get_quality_config())
```

## Frontend Architecture

- **React 18** with TypeScript (Create React App)
- **MSAL React** for Microsoft Azure AD authentication
- **TanStack React Query** for server state management
- **Tailwind CSS** for styling with custom knight-* color scheme and CSS variables
- **shadcn/ui** for modern, accessible UI components (Button, Card, Alert, Badge)
- **Radix UI** for low-level accessible primitives (Slot)
- **class-variance-authority (cva)** for component variant management
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
- `/api/rag/search/` - Primary RAG endpoint (agentic with fallback)
- `/api/rag/agentic/` - Exclusive agentic RAG endpoint (LangGraph only)
- `/api/rag/stats/` - RAG system statistics
- `/api/rag/test-llm/` - LLM provider testing
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

# Test RAG search (agentic with fallback)
curl -X POST http://localhost:8000/api/rag/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 5}'

# Test exclusive agentic RAG
curl -X POST http://localhost:8000/api/rag/agentic/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 5}'

# Force traditional hybrid search
curl -X POST http://localhost:8000/api/rag/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "k": 5, "use_agentic": false}'
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
- **UI Components**: Use shadcn/ui components with consistent variant patterns via cva
- **Styling**: Use Tailwind CSS with custom CSS variables for theming, utilize `cn()` utility for className merging
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