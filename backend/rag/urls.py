from django.urls import path
from . import views
from . import multi_agent_views
from . import llm_management_views

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
    
    # Monitoramento e Administração  
    path('behavior-monitoring/', multi_agent_views.BehaviorMonitoringView.as_view(), name='behavior-monitoring'),
    path('system-health/', multi_agent_views.SystemHealthView.as_view(), name='system-health'),
    path('llm-providers/', multi_agent_views.LLMProviderView.as_view(), name='llm-providers'),
    path('llm-status/', multi_agent_views.LLMStatusView.as_view(), name='llm-status'),
    
    # Utilitários
    path('stats/', views.RAGStatsView.as_view(), name='rag-stats'),
    path('test-llm/', views.TestLLMView.as_view(), name='llm-test'),
    
    # Gestão de LLM Providers (Admin only)
    path('llm/current/', llm_management_views.LLMCurrentView.as_view(), name='llm-current'),
    path('llm/available/', llm_management_views.LLMAvailableView.as_view(), name='llm-available'),
    path('llm/switch/', llm_management_views.LLMSwitchView.as_view(), name='llm-switch'),
    path('llm/test/', llm_management_views.LLMTestView.as_view(), name='llm-test-connection'),
    path('llm/metrics/', llm_management_views.LLMMetricsView.as_view(), name='llm-metrics'),
    path('llm/costs/', llm_management_views.LLMCostsView.as_view(), name='llm-costs'),
    path('llm/history/', llm_management_views.LLMHistoryView.as_view(), name='llm-history'),
    path('llm/debug/', llm_management_views.LLMDebugView.as_view(), name='llm-debug'),
    path('llm/optimization-stats/', llm_management_views.LLMOptimizationStatsView.as_view(), name='llm-optimization-stats'),
]