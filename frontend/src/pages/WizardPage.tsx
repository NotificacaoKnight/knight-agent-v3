import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';
import { MainLayout } from '../components/MainLayout';
import { 
  GraduationCap, 
  BookOpen, 
  Target, 
  Clock, 
  CheckCircle, 
  PlayCircle, 
  Star, 
  TrendingUp,
  Users,
  Calendar,
  Award,
  Lightbulb,
  MapPin
} from 'lucide-react';
import api from '../services/api';

interface LearningPath {
  id: string;
  path_name: string;
  estimated_duration: string;
  created_at: string;
  phases: Phase[];
  milestones: Milestone[];
  certifications: Certification[];
  progress: number;
}

interface Phase {
  phase: number;
  name: string;
  duration: string;
  courses: Course[];
  completed: boolean;
  progress: number;
}

interface Course {
  id: string;
  name: string;
  type: 'obrigatório' | 'opcional' | 'recomendado';
  hours: number;
  format: 'online' | 'presencial' | 'híbrido';
  status: 'not_started' | 'in_progress' | 'completed';
  score?: number;
  progress?: number;
}

interface Milestone {
  id: string;
  title: string;
  description: string;
  target_date: string;
  completed: boolean;
}

interface Certification {
  id: string;
  name: string;
  provider: string;
  level: string;
  recommended: boolean;
  deadline?: string;
}

interface OnboardingProgress {
  user_id: string;
  overall_progress: number;
  current_week: number;
  status: string;
  completed_tasks: number;
  total_tasks: number;
  mentor: string;
  next_steps: string[];
}

export function WizardPage() {
  const [learningPath, setLearningPath] = useState<LearningPath | null>(null);
  const [onboardingProgress, setOnboardingProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [activeTab, setActiveTab] = useState('learning-path');

  // Form states
  const [formData, setFormData] = useState({
    role: '',
    level: '',
    department: '',
    is_new: false,
    interests: [] as string[]
  });

  useEffect(() => {
    fetchLearningPath();
    fetchOnboardingProgress();
  }, []);

  const fetchLearningPath = async () => {
    try {
      const response = await api.get('/api/wizard/learning-path/');
      if (response.data.learning_path) {
        setLearningPath(response.data.learning_path);
      }
    } catch (error) {
      console.error('Erro ao buscar trilha de aprendizado:', error);
    }
  };

  const fetchOnboardingProgress = async () => {
    try {
      const response = await api.get('/api/wizard/onboarding-progress/');
      setOnboardingProgress(response.data);
    } catch (error) {
      console.error('Erro ao buscar progresso do onboarding:', error);
    }
  };

  const createLearningPath = async () => {
    setLoading(true);
    try {
      const response = await api.post('/api/wizard/create-learning-path/', formData);
      setLearningPath(response.data.learning_path);
      setShowCreateForm(false);
    } catch (error) {
      console.error('Erro ao criar trilha de aprendizado:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateCourseProgress = async (courseId: string, progress: number) => {
    try {
      await api.post('/api/wizard/update-progress/', {
        course_id: courseId,
        progress: progress
      });
      fetchLearningPath();
    } catch (error) {
      console.error('Erro ao atualizar progresso:', error);
    }
  };

  const CreateLearningPathForm = () => (
    <Card className="p-6">
      <CardHeader>
        <CardTitle>Criar Minha Trilha de Aprendizado</CardTitle>
        <CardDescription>
          Vamos personalizar sua jornada de desenvolvimento baseada no seu perfil
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Cargo</label>
            <Select value={formData.role} onValueChange={(value: string) => setFormData({...formData, role: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione seu cargo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="analista">Analista</SelectItem>
                <SelectItem value="coordenador">Coordenador</SelectItem>
                <SelectItem value="gerente">Gerente</SelectItem>
                <SelectItem value="diretor">Diretor</SelectItem>
                <SelectItem value="especialista">Especialista</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Nível</label>
            <Select value={formData.level} onValueChange={(value: string) => setFormData({...formData, level: value})}>
              <SelectTrigger>
                <SelectValue placeholder="Selecione seu nível" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="junior">Júnior</SelectItem>
                <SelectItem value="pleno">Pleno</SelectItem>
                <SelectItem value="senior">Sênior</SelectItem>
                <SelectItem value="especialista">Especialista</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Departamento</label>
          <Select value={formData.department} onValueChange={(value: string) => setFormData({...formData, department: value})}>
            <SelectTrigger>
              <SelectValue placeholder="Selecione seu departamento" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="rh">Recursos Humanos</SelectItem>
              <SelectItem value="ti">Tecnologia da Informação</SelectItem>
              <SelectItem value="financeiro">Financeiro</SelectItem>
              <SelectItem value="comercial">Comercial</SelectItem>
              <SelectItem value="operacoes">Operações</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox 
            id="is_new" 
            checked={formData.is_new}
            onCheckedChange={(checked: boolean) => setFormData({...formData, is_new: !!checked})}
          />
          <label htmlFor="is_new" className="text-sm font-medium">
            Sou novo na empresa (menos de 3 meses)
          </label>
        </div>

        <Button onClick={createLearningPath} disabled={loading} className="w-full">
          {loading ? 'Criando...' : 'Criar Trilha Personalizada'}
        </Button>
      </CardContent>
    </Card>
  );

  const LearningPathView = ({ path }: { path: LearningPath }) => (
    <div className="space-y-6">
      {/* Header da Trilha */}
      <Card className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold">{path.path_name}</h2>
            <p className="text-muted-foreground">Duração estimada: {path.estimated_duration}</p>
          </div>
          <Badge variant="outline" className="text-lg px-3 py-1">
            {Math.round(path.progress)}% concluído
          </Badge>
        </div>
        <Progress value={path.progress} className="h-3" />
      </Card>

      {/* Fases da Trilha */}
      <div className="space-y-4">
        {path.phases.map((phase) => (
          <Card key={phase.phase} className={`p-6 ${phase.completed ? 'bg-green-50 border-green-200' : ''}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  phase.completed ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {phase.completed ? <CheckCircle className="w-4 h-4" /> : phase.phase}
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{phase.name}</h3>
                  <p className="text-sm text-muted-foreground">Fase {phase.phase} • {phase.duration}</p>
                </div>
              </div>
              <Progress value={phase.progress} className="w-24" />
            </div>

            {/* Cursos da Fase */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {phase.courses.map((course) => (
                <div key={course.id} className={`p-4 rounded-lg border ${
                  course.status === 'completed' ? 'bg-green-50 border-green-200' :
                  course.status === 'in_progress' ? 'bg-blue-50 border-blue-200' :
                  'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="font-medium">{course.name}</h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={
                          course.type === 'obrigatório' ? 'destructive' :
                          course.type === 'recomendado' ? 'default' : 'secondary'
                        } className="text-xs">
                          {course.type}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {course.hours}h • {course.format}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {course.status === 'completed' && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                      {course.status === 'in_progress' && (
                        <PlayCircle className="w-5 h-5 text-blue-500" />
                      )}
                    </div>
                  </div>

                  {course.status === 'in_progress' && (
                    <div className="mt-3">
                      <Progress value={course.progress || 0} className="h-2" />
                      <p className="text-xs text-muted-foreground mt-1">
                        {course.progress || 0}% concluído
                      </p>
                    </div>
                  )}

                  {course.status === 'completed' && course.score && (
                    <div className="mt-2 flex items-center gap-2">
                      <Star className="w-4 h-4 text-yellow-500" />
                      <span className="text-sm font-medium">Nota: {course.score}%</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Marcos e Certificações */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Marcos */}
        <Card className="p-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Marcos da Jornada
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {path.milestones.map((milestone) => (
              <div key={milestone.id} className="flex items-start gap-3">
                <div className={`w-3 h-3 rounded-full mt-2 ${
                  milestone.completed ? 'bg-green-500' : 'bg-gray-300'
                }`} />
                <div className="flex-1">
                  <h4 className="font-medium">{milestone.title}</h4>
                  <p className="text-sm text-muted-foreground">{milestone.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Meta: {new Date(milestone.target_date).toLocaleDateString('pt-BR')}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Certificações Recomendadas */}
        <Card className="p-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="w-5 h-5" />
              Certificações Recomendadas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {path.certifications.map((cert) => (
              <div key={cert.id} className="p-3 border rounded-lg">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium">{cert.name}</h4>
                    <p className="text-sm text-muted-foreground">{cert.provider}</p>
                    <Badge variant="outline" className="text-xs mt-1">
                      {cert.level}
                    </Badge>
                  </div>
                  {cert.recommended && (
                    <Badge variant="default" className="text-xs">
                      Recomendada
                    </Badge>
                  )}
                </div>
                {cert.deadline && (
                  <p className="text-xs text-orange-600 mt-2">
                    Prazo: {new Date(cert.deadline).toLocaleDateString('pt-BR')}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );

  const OnboardingStatus = ({ progress }: { progress: OnboardingProgress | null }) => {
    if (!progress) {
      return (
        <div className="text-center py-8">
          <GraduationCap className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-muted-foreground">Dados de onboarding não disponíveis</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Progress Overview */}
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-600 mb-2">
            {progress.overall_progress}%
          </div>
          <p className="text-sm text-muted-foreground">Progresso Geral</p>
          <Progress value={progress.overall_progress} className="mt-2" />
        </div>

        {/* Status Atual */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-500" />
            <span className="text-sm">Semana {progress.current_week} do onboarding</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-green-500" />
            <span className="text-sm">Mentor: {progress.mentor}</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-purple-500" />
            <span className="text-sm">
              {progress.completed_tasks}/{progress.total_tasks} tarefas concluídas
            </span>
          </div>
        </div>

        {/* Status Badge */}
        <Badge 
          variant={
            progress.status === 'on_track' ? 'default' :
            progress.status === 'ahead' ? 'secondary' : 'destructive'
          }
          className="w-full justify-center"
        >
          {progress.status === 'on_track' ? 'No Cronograma' :
           progress.status === 'ahead' ? 'Adiantado' : 'Atrasado'}
        </Badge>

        {/* Próximos Passos */}
        {progress.next_steps.length > 0 && (
          <div>
            <h4 className="font-medium mb-2 flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Próximos Passos
            </h4>
            <ul className="space-y-1">
              {progress.next_steps.map((step, index) => (
                <li key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                  <div className="w-1 h-1 bg-gray-400 rounded-full" />
                  {step}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <MainLayout 
      title="🧙 Wizard"
      subtitle="Especialista em Capacitações e Desenvolvimento"
    >
      <div className="h-full overflow-y-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-8">

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="learning-path">Trilha de Aprendizado</TabsTrigger>
            <TabsTrigger value="onboarding">Status Onboarding</TabsTrigger>
            <TabsTrigger value="recommendations">Recomendações</TabsTrigger>
          </TabsList>

          {/* Tab: Trilha de Aprendizado */}
          <TabsContent value="learning-path" className="space-y-6">
            {learningPath ? (
              <LearningPathView path={learningPath} />
            ) : showCreateForm ? (
              <CreateLearningPathForm />
            ) : (
              <Card className="p-12 text-center">
                <GraduationCap className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold mb-2">Crie sua Trilha Personalizada</h3>
                <p className="text-muted-foreground mb-6">
                  Vamos criar um plano de desenvolvimento baseado no seu perfil e objetivos
                </p>
                <Button onClick={() => setShowCreateForm(true)} size="lg">
                  <MapPin className="w-4 h-4 mr-2" />
                  Criar Minha Trilha
                </Button>
              </Card>
            )}
          </TabsContent>

          {/* Tab: Status Onboarding */}
          <TabsContent value="onboarding" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Status Principal */}
              <Card className="lg:col-span-2 p-6">
                <CardHeader>
                  <CardTitle>Progresso do Onboarding</CardTitle>
                  <CardDescription>
                    Acompanhe sua integração na empresa
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <OnboardingStatus progress={onboardingProgress} />
                </CardContent>
              </Card>

              {/* Estatísticas Rápidas */}
              <div className="space-y-4">
                <Card className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
                  <div className="flex items-center gap-3">
                    <Clock className="w-8 h-8" />
                    <div>
                      <div className="text-2xl font-bold">3</div>
                      <div className="text-blue-100">Semanas Ativas</div>
                    </div>
                  </div>
                </Card>
                
                <Card className="p-4 bg-gradient-to-r from-green-500 to-green-600 text-white">
                  <div className="flex items-center gap-3">
                    <BookOpen className="w-8 h-8" />
                    <div>
                      <div className="text-2xl font-bold">8</div>
                      <div className="text-green-100">Módulos Concluídos</div>
                    </div>
                  </div>
                </Card>
                
                <Card className="p-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="w-8 h-8" />
                    <div>
                      <div className="text-2xl font-bold">92%</div>
                      <div className="text-purple-100">Performance</div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Tab: Recomendações */}
          <TabsContent value="recommendations" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Cursos Recomendados */}
              <Card className="p-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Cursos Recomendados
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="p-3 border rounded-lg">
                      <h4 className="font-medium">Liderança Estratégica</h4>
                      <p className="text-xs text-muted-foreground">16h • Online</p>
                      <Badge variant="default" className="text-xs mt-2">Alta Prioridade</Badge>
                    </div>
                    <div className="p-3 border rounded-lg">
                      <h4 className="font-medium">Gestão de Projetos Ágeis</h4>
                      <p className="text-xs text-muted-foreground">24h • Híbrido</p>
                      <Badge variant="secondary" className="text-xs mt-2">Recomendado</Badge>
                    </div>
                    <div className="p-3 border rounded-lg">
                      <h4 className="font-medium">Excel Avançado</h4>
                      <p className="text-xs text-muted-foreground">8h • Online</p>
                      <Badge variant="outline" className="text-xs mt-2">Opcional</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Certificações */}
              <Card className="p-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Award className="w-5 h-5" />
                    Certificações Sugeridas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="p-3 border rounded-lg">
                      <h4 className="font-medium">PMP</h4>
                      <p className="text-xs text-muted-foreground">Project Management Institute</p>
                      <Badge variant="default" className="text-xs mt-2">Essencial</Badge>
                    </div>
                    <div className="p-3 border rounded-lg">
                      <h4 className="font-medium">Scrum Master</h4>
                      <p className="text-xs text-muted-foreground">Scrum Alliance</p>
                      <Badge variant="secondary" className="text-xs mt-2">Relevante</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Próximas Ações */}
              <Card className="p-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Próximas Ações
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-2 bg-blue-50 rounded">
                      <div className="w-2 h-2 bg-blue-500 rounded-full" />
                      <span className="text-sm">Finalizar módulo atual</span>
                    </div>
                    <div className="flex items-center gap-3 p-2 bg-green-50 rounded">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-sm">Agendar mentoria</span>
                    </div>
                    <div className="flex items-center gap-3 p-2 bg-orange-50 rounded">
                      <div className="w-2 h-2 bg-orange-500 rounded-full" />
                      <span className="text-sm">Avaliar desempenho</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
        </div>
      </div>
    </MainLayout>
  );
}

export default WizardPage;