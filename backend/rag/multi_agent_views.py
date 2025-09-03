"""
Views para o sistema multi-agent (Bard e Wizard)
Estende as views existentes do RAG
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
import logging
import json
from datetime import datetime

from .consolidated_multi_agent import consolidated_multi_agent_service
# behavior_monitoring removido - sistema simplificado
from .llm_providers import LLMManager
from documents.models import Document
from authentication.models import User

logger = logging.getLogger(__name__)


class MultiAgentSearchView(APIView):
    """Endpoint principal do sistema multi-agent com Knight supervisor"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            query = request.data.get('query', '')
            user_profile = request.data.get('user_profile', {})
            
            if not query:
                return Response(
                    {'error': 'Query parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Processar com sistema consolidado
            result = consolidated_multi_agent_service.process_query(
                query=query,
                user=getattr(request, 'user', None),
                user_profile=user_profile
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erro no sistema multi-agent: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Erro ao processar consulta: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BardReportsView(APIView):
    """Endpoint específico do agente Bard para relatórios"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Lista relatórios gerados"""
        try:
            # Simular dados até implementar banco real
            reports = [
                {
                    "id": "1",
                    "report_type": "completo",
                    "created_at": "2024-08-08T10:00:00Z",
                    "pdf_path": "/api/downloads/report_1.pdf",
                    "excel_path": "/api/downloads/report_1.xlsx",
                    "data": {
                        "user_name": "Felipe Developer",
                        "summary": {
                            "total_courses": 12,
                            "average_score": 85,
                            "certification_rate": 75,
                            "hours_invested": 156,
                            "courses_in_progress": 3
                        }
                    }
                }
            ]
            
            return Response({
                "reports": reports,
                "total": len(reports)
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar relatórios: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Gera novo relatório"""
        try:
            report_type = request.data.get('report_type', 'completo')
            user_profile = request.data.get('user_profile', {})
            
            # Usar Bard agent para gerar relatório
            query = f"Gere um relatório {report_type} das minhas capacitações"
            
            # Usar sistema consolidado (será roteado para Bard automaticamente)
            result = consolidated_multi_agent_service.process_query(
                query=query,
                user=getattr(request, 'user', None),
                user_profile=user_profile
            )
            
            # Gerar dados específicos do relatório
            report_data = self._generate_report_files(report_type, result)
            
            return Response({
                "report": report_data["report"],
                "files": report_data["files"],
                "charts": report_data["charts"],
                "llm_analysis": result.get("response", "")
            })
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_report_files(self, report_type: str, agent_result: dict) -> dict:
        """Gera arquivos do relatório (simulado)"""
        report_id = f"report_{int(datetime.now().timestamp())}"
        
        # Dados base do relatório
        base_data = {
            "user_name": "Felipe Developer",
            "department": "Tecnologia",
            "role": "Desenvolvedor Sênior",
            "report_date": datetime.now().isoformat(),
            "report_type": report_type,
            "summary": {
                "total_courses": 12,
                "average_score": 85,
                "certification_rate": 75,
                "hours_invested": 156,
                "courses_in_progress": 3
            },
            "completed_courses": [
                {"name": "React Avançado", "score": 92, "hours": 24},
                {"name": "Python para Data Science", "score": 88, "hours": 32},
                {"name": "Docker & Kubernetes", "score": 85, "hours": 16}
            ]
        }
        
        # URLs simuladas dos arquivos
        files = {
            "pdf": f"/api/downloads/{report_id}.pdf",
            "excel": f"/api/downloads/{report_id}.xlsx",
            "json": f"/api/downloads/{report_id}.json"
        }
        
        # Dados para gráficos
        charts = {
            "performance_chart": [
                {"name": "React", "score": 92},
                {"name": "Python", "score": 88},
                {"name": "Docker", "score": 85}
            ],
            "summary_chart": [
                {"name": "Concluídos", "value": 12},
                {"name": "Em Andamento", "value": 3},
                {"name": "Horas Total", "value": 156}
            ]
        }
        
        return {
            "report": base_data,
            "files": files,
            "charts": charts
        }


class WizardTrainingView(APIView):
    """Endpoint específico do agente Wizard para capacitações"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Busca trilha de aprendizado existente"""
        try:
            # Simular dados até implementar banco real
            learning_path = {
                "id": "path_1",
                "path_name": "Trilha de Desenvolvimento Full-Stack",
                "estimated_duration": "4-6 meses",
                "created_at": "2024-08-01T00:00:00Z",
                "progress": 65,
                "phases": [
                    {
                        "phase": 1,
                        "name": "Fundamentos Frontend",
                        "duration": "6 semanas",
                        "completed": True,
                        "progress": 100,
                        "courses": [
                            {
                                "id": "course_1",
                                "name": "React Básico",
                                "type": "obrigatório",
                                "hours": 20,
                                "format": "online",
                                "status": "completed",
                                "score": 92
                            }
                        ]
                    },
                    {
                        "phase": 2,
                        "name": "Backend Development",
                        "duration": "8 semanas", 
                        "completed": False,
                        "progress": 30,
                        "courses": [
                            {
                                "id": "course_2",
                                "name": "Node.js Avançado",
                                "type": "obrigatório",
                                "hours": 32,
                                "format": "híbrido",
                                "status": "in_progress",
                                "progress": 30
                            }
                        ]
                    }
                ],
                "milestones": [
                    {
                        "id": "milestone_1",
                        "title": "Primeiro Projeto React",
                        "description": "Desenvolver aplicação completa",
                        "target_date": "2024-09-15",
                        "completed": True
                    }
                ],
                "certifications": [
                    {
                        "id": "cert_1",
                        "name": "AWS Developer Associate",
                        "provider": "Amazon",
                        "level": "Associate",
                        "recommended": True,
                        "deadline": "2024-12-31"
                    }
                ]
            }
            
            return Response({
                "learning_path": learning_path
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar trilha: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Cria nova trilha de aprendizado"""
        try:
            form_data = request.data
            
            # Usar Wizard agent para criar trilha personalizada
            query = f"""
            Crie uma trilha de capacitação para:
            - Cargo: {form_data.get('role')}
            - Nível: {form_data.get('level')}
            - Departamento: {form_data.get('department')}
            - É novo na empresa: {form_data.get('is_new', False)}
            """
            
            result = consolidated_multi_agent_service.process_query(
                query=query,
                user=getattr(request, 'user', None),
                user_profile=form_data
            )
            
            # Gerar trilha específica baseada nos dados
            learning_path = self._generate_learning_path(form_data, result)
            
            return Response({
                "learning_path": learning_path,
                "wizard_analysis": result.get("response", "")
            })
            
        except Exception as e:
            logger.error(f"Erro ao criar trilha: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_learning_path(self, form_data: dict, agent_result: dict) -> dict:
        """Gera trilha personalizada baseada no perfil"""
        # Personalizar trilha baseada no cargo e nível
        role = form_data.get('role', 'analista')
        level = form_data.get('level', 'junior')
        department = form_data.get('department', 'ti')
        is_new = form_data.get('is_new', False)
        
        # Trilha base personalizada
        base_path = {
            "id": f"path_{int(datetime.now().timestamp())}",
            "path_name": f"Trilha {role.title()} {level.title()} - {department.upper()}",
            "estimated_duration": "3-4 meses" if is_new else "2-3 meses",
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "phases": self._generate_phases_for_role(role, level, is_new),
            "milestones": self._generate_milestones_for_role(role),
            "certifications": self._generate_certifications_for_role(role, department)
        }
        
        return base_path
    
    def _generate_phases_for_role(self, role: str, level: str, is_new: bool) -> list:
        """Gera fases específicas por cargo"""
        base_phases = []
        
        if is_new:
            base_phases.append({
                "phase": 1,
                "name": "Onboarding Corporativo",
                "duration": "2 semanas",
                "completed": False,
                "progress": 0,
                "courses": [
                    {
                        "id": "onb_1",
                        "name": "Cultura e Valores da Empresa",
                        "type": "obrigatório",
                        "hours": 4,
                        "format": "online",
                        "status": "not_started"
                    }
                ]
            })
        
        # Fases específicas por cargo
        if role == "analista":
            base_phases.extend([
                {
                    "phase": 2 if is_new else 1,
                    "name": "Fundamentos Técnicos",
                    "duration": "4 semanas",
                    "completed": False,
                    "progress": 0,
                    "courses": [
                        {
                            "id": "tech_1",
                            "name": "Excel Avançado",
                            "type": "obrigatório",
                            "hours": 16,
                            "format": "online",
                            "status": "not_started"
                        }
                    ]
                }
            ])
        
        return base_phases
    
    def _generate_milestones_for_role(self, role: str) -> list:
        """Gera marcos específicos por cargo"""
        return [
            {
                "id": "m1",
                "title": f"Certificação {role.title()}",
                "description": "Completar avaliação de competências",
                "target_date": "2024-10-15",
                "completed": False
            }
        ]
    
    def _generate_certifications_for_role(self, role: str, department: str) -> list:
        """Gera certificações recomendadas por cargo/departamento"""
        cert_map = {
            "ti": [
                {
                    "id": "cert_ti_1",
                    "name": "AWS Cloud Practitioner",
                    "provider": "Amazon",
                    "level": "Foundational",
                    "recommended": True
                }
            ],
            "rh": [
                {
                    "id": "cert_rh_1", 
                    "name": "People Analytics",
                    "provider": "SHRM",
                    "level": "Professional",
                    "recommended": True
                }
            ]
        }
        
        return cert_map.get(department, [])


class WizardOnboardingView(APIView):
    """Endpoint para progresso de onboarding"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Busca progresso de onboarding"""
        try:
            # Simular dados de onboarding
            progress = {
                "user_id": str(getattr(request.user, 'id', 'anonymous')),
                "overall_progress": 75,
                "current_week": 3,
                "status": "on_track",
                "completed_tasks": 8,
                "total_tasks": 12,
                "mentor": "Ana Silva",
                "next_steps": [
                    "Completar módulo de compliance",
                    "Agendar reunião com mentor",
                    "Finalizar projeto prático"
                ]
            }
            
            return Response(progress)
            
        except Exception as e:
            logger.error(f"Erro ao buscar onboarding: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WizardProgressView(APIView):
    """Endpoint para atualizar progresso de cursos"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Atualiza progresso de curso"""
        try:
            course_id = request.data.get('course_id')
            progress = request.data.get('progress', 0)
            
            # Em produção, salvar no banco de dados
            # Por enquanto, apenas confirmar recebimento
            
            return Response({
                "success": True,
                "message": f"Progresso do curso {course_id} atualizado para {progress}%"
            })
            
        except Exception as e:
            logger.error(f"Erro ao atualizar progresso: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BehaviorMonitoringView(APIView):
    """Endpoint para monitoramento de comportamento inteligente"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Obter métricas de performance"""
        try:
            hours_back = int(request.GET.get('hours', 24))
            metric_type = request.GET.get('type', 'performance')
            
            if metric_type == 'performance':
                data = behavior_monitor.get_performance_summary(hours_back)
            elif metric_type == 'quality':
                data = behavior_monitor.get_quality_insights(hours_back)
            elif metric_type == 'feedback':
                days_back = int(request.GET.get('days', 7))
                data = behavior_monitor.get_user_feedback_summary(days_back)
            else:
                return Response(
                    {'error': 'Invalid metric type. Use: performance, quality, or feedback'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                "success": True,
                "metric_type": metric_type,
                "data": data
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Registrar feedback do usuário"""
        try:
            query_hash = request.data.get('query_hash')
            feedback_type = request.data.get('feedback_type')
            feedback_details = request.data.get('feedback_details', '')
            
            if not query_hash or not feedback_type:
                return Response(
                    {'error': 'query_hash and feedback_type are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valid_feedback_types = ['helpful', 'not_helpful', 'incomplete', 'wrong']
            if feedback_type not in valid_feedback_types:
                return Response(
                    {'error': f'Invalid feedback_type. Must be one of: {valid_feedback_types}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Contexto do usuário
            user_context = {}
            if hasattr(request, 'user') and request.user:
                user_context = {
                    'department': getattr(request.user, 'department', None),
                    'role': getattr(request.user, 'role', None)
                }
            
            behavior_monitor.log_user_feedback(
                query_hash=int(query_hash),
                feedback_type=feedback_type,
                feedback_details=feedback_details,
                user_context=user_context
            )
            
            return Response({
                "success": True,
                "message": "Feedback registrado com sucesso"
            })
            
        except Exception as e:
            logger.error(f"Erro ao registrar feedback: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SystemHealthView(APIView):
    """Endpoint para status de saúde do sistema inteligente"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Obter status geral do sistema"""
        try:
            # Performance das últimas 6 horas
            performance = behavior_monitor.get_performance_summary(6)
            
            # Insights de qualidade das últimas 12 horas  
            quality = behavior_monitor.get_quality_insights(12)
            
            # Status dos agentes
            agent_status = {}
            if "error" not in performance:
                for agent, data in performance.get("agent_performance", {}).items():
                    status_level = "healthy"
                    if data["avg_quality"] < 0.4:
                        status_level = "critical"
                    elif data["avg_quality"] < 0.6:
                        status_level = "warning"
                    
                    agent_status[agent] = {
                        "status": status_level,
                        "quality": data["avg_quality"],
                        "avg_response_time": data["avg_time"],
                        "request_count": data["count"]
                    }
            
            # Status geral do sistema
            overall_status = "healthy"
            alerts = []
            
            if "error" not in performance:
                avg_quality = performance["summary"]["avg_quality_score"]
                avg_time = performance["summary"]["avg_processing_time_ms"]
                
                if avg_quality < 0.4:
                    overall_status = "critical"
                    alerts.append("Qualidade geral abaixo do aceitável")
                elif avg_quality < 0.6:
                    overall_status = "warning"
                    alerts.append("Qualidade geral precisa de atenção")
                
                if avg_time > 20000:  # 20 segundos
                    if overall_status == "healthy":
                        overall_status = "warning"
                    alerts.append("Tempo de resposta alto")
            
            # Recomendações
            recommendations = []
            if "error" not in quality and quality.get("recommendations"):
                recommendations = quality["recommendations"]
            
            return Response({
                "overall_status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "alerts": alerts,
                "agent_status": agent_status,
                "performance_summary": performance.get("summary", {}),
                "quality_summary": quality.get("quality_issues", {}),
                "recommendations": recommendations,
                "system_info": {
                    "intelligent_behavior": True,
                    "monitoring_enabled": True,
                    "consolidated_multi_agent": True
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter status do sistema: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMProviderView(APIView):
    """Endpoint para gerenciar provedores LLM"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Obter informações dos provedores LLM"""
        try:
            # Obter instância do LLM manager
            llm_manager = LLMManager()
            
            # Provedor atual
            current_provider = llm_manager.primary_provider
            
            # Provedores disponíveis
            available_providers = llm_manager.get_available_providers()
            
            # Informações detalhadas dos provedores
            provider_info = {
                'openai': {
                    'name': 'OpenAI (GPT-4, GPT-3.5)',
                    'description': 'Qualidade alta, custo médio',
                    'icon': '🤖',
                    'models': ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']
                },
                'deepseek': {
                    'name': 'DeepSeek',
                    'description': 'Custo baixo, boa performance',
                    'icon': '🧠',
                    'models': ['deepseek-chat']
                },
                'gemini': {
                    'name': 'Google Gemini',
                    'description': 'Gratuito com limite, rápido',
                    'icon': '🌟',
                    'models': ['gemini-1.5-flash', 'gemini-1.5-pro']
                },
                'cohere': {
                    'name': 'Cohere',
                    'description': 'Otimizado para RAG',
                    'icon': '🎯',
                    'models': ['command-r-plus', 'command-r']
                },
                'groq': {
                    'name': 'Groq',
                    'description': 'Muito rápido, menos preciso',
                    'icon': '⚡',
                    'models': ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768']
                }
            }
            
            # Status de cada provedor
            provider_status = {}
            for provider_name in provider_info.keys():
                if provider_name in llm_manager.providers:
                    provider_status[provider_name] = {
                        **provider_info[provider_name],
                        'available': provider_name in available_providers,
                        'is_current': provider_name == current_provider
                    }
            
            return Response({
                "current_provider": current_provider,
                "available_providers": available_providers,
                "fallback_order": llm_manager.fallback_order,
                "providers": provider_status
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter provedores LLM: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Alterar provedor LLM em tempo real"""
        try:
            new_provider = request.data.get('provider')
            
            if not new_provider:
                return Response(
                    {'error': 'Provider parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obter instância do LLM manager
            llm_manager = LLMManager()
            
            # Verificar se o provedor é válido
            valid_providers = ['openai', 'deepseek', 'gemini', 'cohere', 'groq', 'together']
            if new_provider not in valid_providers:
                return Response(
                    {'error': f'Invalid provider. Valid options: {valid_providers}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar se o provedor está disponível
            if new_provider not in llm_manager.providers:
                return Response(
                    {'error': f'Provider {new_provider} not configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not llm_manager.providers[new_provider].is_available():
                return Response(
                    {'error': f'Provider {new_provider} is not available (missing API key)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Testar o provedor antes de alterar
            test_result = llm_manager.providers[new_provider].generate_response(
                "Teste", max_tokens=10, temperature=0.1
            )
            
            if not test_result.get('success', False):
                return Response(
                    {'error': f'Provider {new_provider} test failed: {test_result.get("error", "Unknown error")}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Alterar provedor no sistema
            old_provider = llm_manager.primary_provider
            llm_manager.primary_provider = new_provider
            
            # Atualizar configuração no Django settings (em memória)
            from django.conf import settings
            settings.LLM_PROVIDER = new_provider
            
            # Atualizar no consolidated_multi_agent_service
            consolidated_multi_agent_service.llm_manager.primary_provider = new_provider
            
            return Response({
                "success": True,
                "message": f"Provedor alterado de {old_provider} para {new_provider}",
                "old_provider": old_provider,
                "new_provider": new_provider,
                "test_response": test_result.get('response', ''),
                "note": "Alteração aplicada em tempo real - sem necessidade de reiniciar"
            })
            
        except Exception as e:
            logger.error(f"Erro ao alterar provedor LLM: {str(e)}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMStatusView(APIView):
    """Endpoint simplificado para status do LLM no header"""
    permission_classes = [AllowAny]  # Controle de admin será feito no frontend
    
    def get(self, request):
        """Obter status atual do LLM para exibição no header"""
        try:
            from .llm_providers import get_llm_manager
            
            # Usar LLMManager como fonte única de verdade
            llm_manager = get_llm_manager()
            current_provider = llm_manager.get_current_provider()
            
            # Informações dos provedores
            provider_info = {
                'openai': {'name': 'OpenAI', 'color': '#10a37f'},
                'deepseek': {'name': 'DeepSeek', 'color': '#6366f1'},
                'gemini': {'name': 'Gemini', 'color': '#4285f4'},
                'cohere': {'name': 'Cohere', 'color': '#d946ef'},
                'groq': {'name': 'Groq', 'color': '#f59e0b'},
                'together': {'name': 'Together', 'color': '#8b5cf6'}
            }
            
            provider_data = provider_info.get(current_provider, {
                'name': current_provider.title(),
                'color': '#6b7280'
            })
            
            # Verificar se o provedor está funcionando
            try:
                is_healthy = current_provider in llm_manager.get_available_providers()
            except:
                is_healthy = False
            
            return Response({
                "current_provider": current_provider,
                "provider_name": provider_data['name'],
                "provider_color": provider_data['color'],
                "is_healthy": is_healthy,
                "status": "healthy" if is_healthy else "error"
            })
            
        except Exception as e:
            return Response({
                "current_provider": "error",
                "provider_name": "Error",
                "provider_color": "#ef4444",
                "is_healthy": False,
                "status": "error",
                "error": str(e)
            })