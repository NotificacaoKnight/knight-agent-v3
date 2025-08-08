# Context Engineering - Implementação Bard e Wizard Agents no Sistema Knight

## 🎯 Objetivo Principal
Adicionar dois novos agentes (Bard e Wizard) ao sistema Knight existente, cada um com sua própria interface dedicada, mantendo a arquitetura base do sistema.

## 🏗️ Arquitetura de Implementação

### 1. Estrutura de Navegação

```tsx
// App.tsx - Adicionar novas rotas
<Routes>
  <Route path="/chat" element={<ChatPage />} />        {/* Knight existente */}
  <Route path="/bard" element={<BardPage />} />        {/* NOVO - Relatórios */}
  <Route path="/wizard" element={<WizardPage />} />    {/* NOVO - Capacitações */}
</Routes>

// components/Navigation.tsx - Menu lateral
const menuItems = [
  { path: '/chat', label: 'Knight - Assistente RH', icon: '⚔️' },
  { path: '/bard', label: 'Bard - Relatórios', icon: '🎭' },
  { path: '/wizard', label: 'Wizard - Capacitações', icon: '🧙' }
];
```

### 2. Implementar Agentes (Backend)

#### Bard Agent - Gerador de Relatórios
**Arquivo**: `backend/agents/bard_agent.py`

**Responsabilidades**:
- Gerar relatórios de pontuação de capacitações
- Criar análises de performance
- Exportar dados em PDF/Excel
- Visualizar progresso com gráficos

```python
from typing import Dict, List
from datetime import datetime
import json
from fpdf import FPDF
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class BardAgent:
    def __init__(self):
        self.name = "Bard"
        self.description = "Especialista em relatórios e análises"
        
    def generate_training_report(self, user_id: str, report_type: str = "completo") -> Dict:
        """Gera relatório de capacitações do colaborador"""
        
        # Buscar dados do usuário
        user_data = self._get_user_training_data(user_id)
        
        # Estrutura do relatório
        report = {
            "user_name": user_data["name"],
            "department": user_data["department"],
            "role": user_data["role"],
            "report_date": datetime.now().isoformat(),
            "report_type": report_type,
            "summary": {
                "total_courses": len(user_data["completed_courses"]),
                "average_score": self._calculate_average_score(user_data["completed_courses"]),
                "certification_rate": self._calculate_certification_rate(user_data["completed_courses"]),
                "hours_invested": sum(c["hours"] for c in user_data["completed_courses"]),
                "courses_in_progress": len(user_data["in_progress_courses"])
            },
            "completed_courses": user_data["completed_courses"],
            "in_progress_courses": user_data["in_progress_courses"],
            "performance_analysis": self._analyze_performance(user_data),
            "recommendations": self._generate_recommendations(user_data)
        }
        
        # Gerar visualizações
        charts = self._create_charts(report)
        
        # Salvar arquivos
        files = {
            "pdf": self._save_as_pdf(report, charts),
            "excel": self._save_as_excel(report),
            "json": self._save_as_json(report)
        }
        
        return {
            "report": report,
            "files": files,
            "charts": charts
        }
    
    def _create_charts(self, report: Dict) -> Dict:
        """Cria gráficos para o relatório"""
        charts = {}
        
        # Gráfico de evolução de notas
        if report["completed_courses"]:
            plt.figure(figsize=(10, 6))
            courses = report["completed_courses"]
            names = [c["name"][:20] + "..." if len(c["name"]) > 20 else c["name"] for c in courses]
            scores = [c["score"] for c in courses]
            
            plt.bar(names, scores, color='skyblue')
            plt.axhline(y=70, color='r', linestyle='--', label='Nota mínima')
            plt.xticks(rotation=45, ha='right')
            plt.ylabel('Pontuação (%)')
            plt.title('Pontuação por Curso')
            plt.legend()
            plt.tight_layout()
            
            chart_path = f"reports/charts/scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path)
            plt.close()
            
            charts["scores"] = chart_path
        
        return charts
    
    def _save_as_pdf(self, report: Dict, charts: Dict) -> str:
        """Salva relatório em PDF"""
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 15, "Relatório de Capacitações", 0, 1, "C")
        
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"{report['user_name']} - {report['department']}", 0, 1, "C")
        
        # Resumo
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Resumo Executivo", 0, 1)
        
        pdf.set_font("Arial", "", 11)
        summary = report['summary']
        pdf.cell(0, 8, f"Total de cursos concluídos: {summary['total_courses']}", 0, 1)
        pdf.cell(0, 8, f"Média geral: {summary['average_score']:.1f}%", 0, 1)
        pdf.cell(0, 8, f"Taxa de certificação: {summary['certification_rate']:.1f}%", 0, 1)
        pdf.cell(0, 8, f"Horas investidas: {summary['hours_invested']}h", 0, 1)
        
        # Cursos concluídos
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Cursos Concluídos", 0, 1)
        
        pdf.set_font("Arial", "", 10)
        for course in report['completed_courses']:
            pdf.cell(0, 6, f"• {course['name']} - Nota: {course['score']}%", 0, 1)
        
        # Salvar
        filename = f"reports/capacitacao_{report['user_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf.output(filename)
        
        return filename
```

#### Wizard Agent - Especialista em Capacitações
**Arquivo**: `backend/agents/wizard_agent.py`

```python
class WizardAgent:
    def __init__(self):
        self.name = "Wizard"
        self.description = "Especialista em capacitações e onboarding"
        
    def create_learning_path(self, user_profile: Dict) -> Dict:
        """Cria trilha de aprendizado personalizada"""
        
        role = user_profile["role"]
        level = user_profile["level"]
        department = user_profile["department"]
        
        # Catálogo de cursos por área
        learning_path = {
            "user_id": user_profile["user_id"],
            "created_at": datetime.now().isoformat(),
            "path_name": f"Trilha {role} - {level}",
            "estimated_duration": "3 meses",
            "phases": []
        }
        
        # Fase 1: Onboarding
        if user_profile.get("is_new", False):
            learning_path["phases"].append({
                "phase": 1,
                "name": "Onboarding Knightec",
                "duration": "2 semanas",
                "courses": [
                    {
                        "id": "ONB001",
                        "name": "Cultura e Valores Knightec",
                        "type": "obrigatório",
                        "hours": 4,
                        "format": "online"
                    },
                    {
                        "id": "ONB002", 
                        "name": "Processos e Ferramentas",
                        "type": "obrigatório",
                        "hours": 8,
                        "format": "presencial"
                    }
                ]
            })
        
        # Fase 2: Fundamentos do Cargo
        learning_path["phases"].append({
            "phase": 2,
            "name": f"Fundamentos - {role}",
            "duration": "4 semanas",
            "courses": self._get_fundamental_courses(role, level)
        })
        
        # Fase 3: Especialização
        learning_path["phases"].append({
            "phase": 3,
            "name": "Especialização e Desenvolvimento",
            "duration": "6 semanas",
            "courses": self._get_specialization_courses(role, level, user_profile.get("interests", []))
        })
        
        # Adicionar marcos e certificações
        learning_path["milestones"] = self._define_milestones(learning_path)
        learning_path["certifications"] = self._recommend_certifications(role, level)
        
        return learning_path
    
    def track_onboarding_progress(self, user_id: str) -> Dict:
        """Acompanha progresso do onboarding"""
        
        # Buscar dados do usuário
        progress_data = self._get_user_progress(user_id)
        
        # Calcular métricas
        total_tasks = len(progress_data["onboarding_tasks"])
        completed_tasks = sum(1 for task in progress_data["onboarding_tasks"] if task["completed"])
        
        progress = {
            "user_id": user_id,
            "overall_progress": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "current_week": progress_data["current_week"],
            "status": self._determine_status(completed_tasks, total_tasks),
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "next_steps": self._get_next_steps(progress_data),
            "mentor": progress_data.get("mentor", "Não atribuído"),
            "feedback": progress_data.get("feedback", [])
        }
        
        return progress
```

### 3. APIs Específicas por Agente

```python
# api/views/bard_views.py
from rest_framework.decorators import api_view
from agents.bard_agent import BardAgent

@api_view(['POST'])
def generate_report(request):
    """Endpoint específico do Bard para gerar relatórios"""
    user_id = request.user.id
    report_type = request.data.get('report_type', 'completo')
    
    bard = BardAgent()
    result = bard.generate_training_report(user_id, report_type)
    
    return Response({
        "success": True,
        "report": result["report"],
        "files": result["files"],
        "message": "Relatório gerado com sucesso!"
    })

@api_view(['GET'])
def list_reports(request):
    """Lista relatórios anteriores do usuário"""
    user_id = request.user.id
    reports = Report.objects.filter(user_id=user_id).order_by('-created_at')[:10]
    
    return Response({
        "reports": ReportSerializer(reports, many=True).data
    })

# api/views/wizard_views.py
@api_view(['POST'])
def create_learning_path(request):
    """Endpoint do Wizard para criar trilha de aprendizado"""
    user_profile = {
        "user_id": request.user.id,
        "role": request.data.get('role'),
        "level": request.data.get('level'),
        "department": request.data.get('department'),
        "is_new": request.data.get('is_new', False),
        "interests": request.data.get('interests', [])
    }
    
    wizard = WizardAgent()
    learning_path = wizard.create_learning_path(user_profile)
    
    # Salvar no banco
    LearningPath.objects.create(
        user_id=request.user.id,
        data=learning_path
    )
    
    return Response({
        "success": True,
        "learning_path": learning_path
    })
```

### 4. Interfaces Frontend Dedicadas

#### Página do Bard
```tsx
// pages/BardPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export function BardPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const generateReport = async (reportType: string) => {
    setLoading(true);
    try {
      const response = await api.post('/api/bard/generate-report', {
        report_type: reportType
      });
      
      // Atualizar lista de relatórios
      fetchReports();
    } catch (error) {
      console.error('Erro ao gerar relatório:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <span>🎭</span> Bard - Central de Relatórios
        </h1>
        <p className="text-muted-foreground mt-2">
          Gere relatórios detalhados sobre suas capacitações e performance
        </p>
      </div>
      
      {/* Ações principais */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="p-4">
          <h3 className="font-semibold mb-2">Relatório Completo</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Análise detalhada de todas as suas capacitações
          </p>
          <Button 
            onClick={() => generateReport('completo')}
            disabled={loading}
            className="w-full"
          >
            Gerar Relatório
          </Button>
        </Card>
        
        <Card className="p-4">
          <h3 className="font-semibold mb-2">Relatório Mensal</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Resumo das atividades do último mês
          </p>
          <Button 
            onClick={() => generateReport('mensal')}
            disabled={loading}
            variant="secondary"
            className="w-full"
          >
            Gerar Mensal
          </Button>
        </Card>
        
        <Card className="p-4">
          <h3 className="font-semibold mb-2">Certificações</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Status das suas certificações
          </p>
          <Button 
            onClick={() => generateReport('certificacoes')}
            disabled={loading}
            variant="secondary"
            className="w-full"
          >
            Ver Certificações
          </Button>
        </Card>
      </div>
      
      {/* Lista de relatórios gerados */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Relatórios Recentes</h2>
        <ReportsList reports={reports} />
      </Card>
    </div>
  );
}
```

#### Página do Wizard
```tsx
// pages/WizardPage.tsx
export function WizardPage() {
  const [learningPath, setLearningPath] = useState(null);
  const [onboardingProgress, setOnboardingProgress] = useState(null);
  
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <span>🧙</span> Wizard - Capacitações e Desenvolvimento
        </h1>
        <p className="text-muted-foreground mt-2">
          Sua jornada de aprendizado personalizada
        </p>
      </div>
      
      {/* Dashboard de progresso */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Progresso Geral */}
        <Card className="lg:col-span-2 p-6">
          <h2 className="text-xl font-semibold mb-4">Minha Trilha de Aprendizado</h2>
          {learningPath ? (
            <LearningPathView path={learningPath} />
          ) : (
            <CreateLearningPath onComplete={setLearningPath} />
          )}
        </Card>
        
        {/* Status Onboarding */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Status Onboarding</h2>
          <OnboardingStatus progress={onboardingProgress} />
        </Card>
      </div>
      
      {/* Cursos em andamento */}
      <Card className="mt-6 p-6">
        <h2 className="text-xl font-semibold mb-4">Cursos em Andamento</h2>
        <CoursesInProgress />
      </Card>
    </div>
  );
}
```

### 5. Modelos de Dados

```python
# models/reports.py
class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50)
    data = models.JSONField()
    pdf_path = models.CharField(max_length=255)
    excel_path = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

# models/learning.py  
class LearningPath(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class CourseProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course_id = models.CharField(max_length=50)
    course_name = models.CharField(max_length=200)
    status = models.CharField(max_length=50)
    score = models.FloatField(null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
```

## 🚀 Comandos para Implementação

```bash
# 1. Backend - Criar estrutura
mkdir -p backend/agents
mkdir -p backend/api/views
mkdir -p backend/reports/charts
touch backend/agents/{bard_agent.py,wizard_agent.py}
touch backend/api/views/{bard_views.py,wizard_views.py}

# 2. Frontend - Criar páginas
mkdir -p frontend/src/pages
touch frontend/src/pages/{BardPage.tsx,WizardPage.tsx}

# 3. Instalar dependências
pip install fpdf2 pandas matplotlib seaborn openpyxl

# 4. Migrações
python manage.py makemigrations
python manage.py migrate

# 5. URLs
# Adicionar em urls.py:
# path('api/bard/', include('api.views.bard_views')),
# path('api/wizard/', include('api.views.wizard_views')),
```

## ⚠️ Pontos de Atenção

1. **Isolamento**: Cada agente opera independentemente
2. **Permissões**: Usuários só veem seus próprios dados
3. **Storage**: Configurar limpeza periódica de relatórios antigos
4. **Performance**: Cache de dados frequentemente acessados

## 📊 Estrutura de Navegação Final

```
Sistema Knight
├── ⚔️ Knight (Chat) - Assistente RH
├── 🎭 Bard - Central de Relatórios
│   ├── Gerar Relatório Completo
│   ├── Relatório Mensal
│   ├── Status de Certificações
│   └── Histórico de Relatórios
└── 🧙 Wizard - Capacitações
    ├── Minha Trilha de Aprendizado
    ├── Status Onboarding
    ├── Cursos em Andamento
    └── Recomendações Personalizadas
```