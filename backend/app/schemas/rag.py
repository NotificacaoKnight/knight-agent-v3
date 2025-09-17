"""
Pydantic schemas for RAG endpoints
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search query request"""
    query: str = Field(..., description="Search query text")
    k: int = Field(5, description="Number of results to return", ge=1, le=20)
    search_type: str = Field("hybrid", description="Search type: hybrid, semantic, keyword")
    use_agentic: bool = Field(True, description="Use agentic RAG with LangGraph")
    threshold: Optional[float] = Field(None, description="Similarity/score threshold", ge=0.0, le=1.0)
    filter_document_ids: Optional[List[int]] = Field(None, description="Filter by document IDs")
    include_metadata: bool = Field(True, description="Include metadata in results")


class ChunkResult(BaseModel):
    """Search result chunk"""
    chunk_id: int
    document_id: int
    document_title: Optional[str] = None
    content: str
    chunk_index: int
    similarity: Optional[float] = None
    score: Optional[float] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response"""
    success: bool
    query: str
    results: List[ChunkResult]
    total_results: int
    search_type: str
    search_time_ms: int
    metadata: Optional[Dict[str, Any]] = None


class RAGQuery(BaseModel):
    """RAG query for answer generation"""
    query: str = Field(..., description="User question")
    context_size: int = Field(5, description="Number of context chunks to use")
    max_tokens: int = Field(1000, description="Maximum tokens in response")
    temperature: float = Field(0.7, description="Response temperature", ge=0.0, le=1.0)
    use_agentic: bool = Field(True, description="Use agentic RAG")
    include_sources: bool = Field(True, description="Include source references")
    language: str = Field("pt", description="Response language (pt, en)")
    llm_provider: Optional[str] = Field(None, description="Specific LLM provider to use")


class RAGResponse(BaseModel):
    """RAG answer response"""
    success: bool
    query: str
    answer: str
    sources: Optional[List[ChunkResult]] = None
    llm_provider: str
    response_time_ms: int
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class AgenticRAGQuery(BaseModel):
    """Agentic RAG query with advanced options"""
    query: str = Field(..., description="User question")
    max_search_attempts: int = Field(3, description="Maximum search refinement attempts")
    quality_threshold: float = Field(0.6, description="Quality threshold for response")
    max_context_length: int = Field(8000, description="Maximum context length in characters")
    enable_multi_agent: bool = Field(False, description="Enable multi-agent system")
    agent_type: Optional[str] = Field(None, description="Specific agent: knight, bard, wizard")
    include_knowledge_resources: bool = Field(True, description="Include knowledge resources")
    max_links: int = Field(3, description="Maximum useful links to include")
    max_documents: int = Field(2, description="Maximum downloadable documents to include")


class AgenticRAGResponse(BaseModel):
    """Agentic RAG response with metadata"""
    success: bool
    query: str
    answer: str
    sources: List[ChunkResult]
    search_refinements: int
    quality_score: float
    agent_used: Optional[str] = None
    useful_links: Optional[List[Dict[str, Any]]] = None
    downloadable_documents: Optional[List[Dict[str, Any]]] = None
    reasoning_steps: Optional[List[str]] = None
    llm_provider: str
    response_time_ms: int
    metadata: Dict[str, Any]


class VectorStatsResponse(BaseModel):
    """Vector store statistics"""
    total_documents: int
    total_chunks: int
    chunks_with_embeddings: int
    embedding_coverage: float
    service_type: str
    embedding_model: str
    embedding_dimension: int
    index_status: Optional[str] = None


class LLMProviderInfo(BaseModel):
    """LLM provider information"""
    type: str
    available: bool
    info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMProvidersResponse(BaseModel):
    """Available LLM providers"""
    providers: List[LLMProviderInfo]
    current_provider: str
    fallback_order: List[str]


class TestLLMQuery(BaseModel):
    """Test LLM query"""
    prompt: str = Field(..., description="Test prompt")
    provider: Optional[str] = Field(None, description="Specific provider to test")
    max_tokens: int = Field(100, description="Maximum tokens")
    temperature: float = Field(0.7, description="Temperature")


class TestLLMResponse(BaseModel):
    """Test LLM response"""
    success: bool
    provider: str
    response: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: int


class DocumentUploadRequest(BaseModel):
    """Document upload request"""
    title: str = Field(..., description="Document title")
    enable_ocr: bool = Field(False, description="Enable OCR for scanned documents")
    chunk_size: Optional[int] = Field(None, description="Custom chunk size")
    chunk_overlap: Optional[int] = Field(None, description="Custom chunk overlap")


class DocumentProcessingStatus(BaseModel):
    """Document processing status"""
    document_id: int
    title: str
    status: str
    progress: Optional[float] = None
    chunks_created: Optional[int] = None
    embeddings_generated: Optional[int] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


class IndexUpdateRequest(BaseModel):
    """Index update request"""
    rebuild_bm25: bool = Field(True, description="Rebuild BM25 index")
    update_vector_index: bool = Field(True, description="Update vector index")
    clear_cache: bool = Field(False, description="Clear all caches")