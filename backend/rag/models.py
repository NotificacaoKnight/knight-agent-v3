from django.db import models
from django.contrib.auth import get_user_model
from documents.models import Document

User = get_user_model()

class VectorStore(models.Model):
    """Armazena configurações da base vetorial"""
    name = models.CharField(max_length=100, unique=True)
    embedding_model = models.CharField(max_length=100)
    dimension = models.IntegerField()
    index_path = models.CharField(max_length=500)
    
    # Configurações
    chunk_size = models.IntegerField(default=700)
    chunk_overlap = models.IntegerField(default=100)
    
    # Metadados
    documents_count = models.IntegerField(default=0)
    vectors_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.vectors_count} vectors)"

class SearchQuery(models.Model):
    """Log de consultas de busca"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query_text = models.TextField()
    query_embedding = models.JSONField(null=True, blank=True)
    
    # Configurações da busca
    search_type = models.CharField(max_length=20, default='hybrid')  # semantic, bm25, hybrid
    semantic_weight = models.FloatField(default=0.7)
    bm25_weight = models.FloatField(default=0.3)
    top_k = models.IntegerField(default=5)
    
    # Resultados
    results_count = models.IntegerField(default=0)
    results = models.JSONField(default=list)
    
    # Performance
    search_duration_ms = models.IntegerField(null=True, blank=True)
    embedding_duration_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}..."

class SearchResult(models.Model):
    """Resultado individual de busca"""
    query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='search_results')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    chunk_index = models.IntegerField()
    
    # Scores
    semantic_score = models.FloatField(null=True, blank=True)
    bm25_score = models.FloatField(null=True, blank=True)
    combined_score = models.FloatField()
    
    # Conteúdo
    content = models.TextField()
    
    # Metadados
    rank = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['query', 'rank']
    
    def __str__(self):
        return f"Result {self.rank} for query {self.query.id}"

class RagMetrics(models.Model):
    """Métricas do sistema RAG"""
    date = models.DateField(auto_now_add=True)
    
    # Consultas
    total_queries = models.IntegerField(default=0)
    successful_queries = models.IntegerField(default=0)
    failed_queries = models.IntegerField(default=0)
    
    # Performance média
    avg_search_duration_ms = models.FloatField(null=True, blank=True)
    avg_embedding_duration_ms = models.FloatField(null=True, blank=True)
    
    # Top queries
    top_queries = models.JSONField(default=list)
    
    # Documentos mais relevantes
    top_documents = models.JSONField(default=list)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"RAG Metrics - {self.date}"