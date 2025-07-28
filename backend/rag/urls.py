from django.urls import path
from . import views

urlpatterns = [
    # Endpoint principal com fallback automático
    path('search/', views.SearchView.as_view(), name='rag-search'),
    
    # Endpoint exclusivo para RAG Agentic (LangGraph)
    path('agentic/', views.AgenticSearchView.as_view(), name='agentic-rag-search'),
    
    # Utilitários
    path('stats/', views.StatsView.as_view(), name='rag-stats'),
    path('test-llm/', views.LLMTestView.as_view(), name='llm-test'),
]