from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.SearchView.as_view(), name='rag-search'),
    path('stats/', views.StatsView.as_view(), name='rag-stats'),
    path('test-llm/', views.LLMTestView.as_view(), name='llm-test'),
]