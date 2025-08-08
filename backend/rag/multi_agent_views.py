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