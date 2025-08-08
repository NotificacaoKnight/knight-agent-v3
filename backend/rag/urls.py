from django.urls import path
from . import views
from . import multi_agent_views

urlpatterns = [
    # Endpoint principal com fallback automático
    path('search/', views.SearchView.as_view(), name='rag-search'),
    
    # Endpoint exclusivo para RAG Agentic (LangGraph)
    path('agentic/', views.AgenticSearchView.as_view(), name='agentic-rag-search'),
    
    # MULTI-AGENT ENDPOINTS
    # Endpoint principal multi-agent com Knight supervisor
    path('multi-agent/', multi_agent_views.MultiAgentSearchView.as_view(), name='multi-agent-search'),
    
    # Bard Agent - Central de Relatórios
    path('bard/reports/', multi_agent_views.BardReportsView.as_view(), name='bard-reports'),
    path('bard/generate-report/', multi_agent_views.BardReportsView.as_view(), name='bard-generate-report'),
    
    # Wizard Agent - Capacitações
    path('wizard/learning-path/', multi_agent_views.WizardTrainingView.as_view(), name='wizard-learning-path'),
    path('wizard/create-learning-path/', multi_agent_views.WizardTrainingView.as_view(), name='wizard-create-path'),
    path('wizard/onboarding-progress/', multi_agent_views.WizardOnboardingView.as_view(), name='wizard-onboarding'),
    path('wizard/update-progress/', multi_agent_views.WizardProgressView.as_view(), name='wizard-update-progress'),
    
    # Utilitários
    path('stats/', views.RAGStatsView.as_view(), name='rag-stats'),
    path('test-llm/', views.TestLLMView.as_view(), name='llm-test'),
]