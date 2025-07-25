from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.SearchView.as_view(), name='rag-search'),
    path('stats/', views.StatsView.as_view(), name='rag-stats'),
    path('test-llm/', views.LLMTestView.as_view(), name='llm-test'),
    path('cache/stats/', views.EmbeddingCacheStatsView.as_view(), name='cache-stats'),
    path('cache/clear/', views.EmbeddingCacheClearView.as_view(), name='cache-clear'),
    path('pool/stats/', views.HTTPPoolStatsView.as_view(), name='pool-stats'),
]