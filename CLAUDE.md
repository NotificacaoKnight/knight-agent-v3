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

## Development Commands

### Backend (Django)

```bash
# Initial setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure before running

# Database operations
python manage.py migrate
python manage.py createsuperuser

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

### Frontend (React/Next.js)

```bash
cd frontend
npm install
npm start  # Development server on port 3000
npm run build  # Production build
npm test  # Run tests
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

### Testing Document Processing

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

### Authentication Flow

- Frontend redirects to Microsoft OAuth
- Backend validates tokens via MSAL
- Custom Django User model stores Microsoft ID + company info
- Session tokens for subsequent API calls

### Document Processing Pipeline

- Upload → Celery task → Docling conversion → Chunking → Embedding → Indexing
- Status tracking through `ProcessingJob` model
- Error handling with retry logic

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
```