import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '../components/MainLayout';
import { 
  MessageSquare, 
  FileText, 
  Download, 
  Users,
  Clock,
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Loader2
} from 'lucide-react';
import { Card } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { ChartContainer } from '../components/ui/chart';
import { ChartAreaInteractive } from '../components/charts/ChartAreaInteractive';

interface DashboardStats {
  totalChats: number;
  totalDocuments: number;
  totalDownloads: number;
  activeUsers: number;
  avgResponseTime: number;
  systemUptime: number;
}

interface ActivityData {
  date: string;
  conversas: number;
  documentos: number;
}

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activityData, setActivityData] = useState<ActivityData[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Carregar dados reais do sistema
  useEffect(() => {
    const loadStats = async () => {
      setLoading(true);
      
      try {
        // Obter token de autenticação
        const token = localStorage.getItem('sessionToken');
        if (!token) {
          console.warn('DashboardPage - Token de autenticação não encontrado');
        }

        // Fazer chamadas paralelas para todas as APIs de estatísticas
        const [documentsRes, chatRes, activityRes] = await Promise.all([
          fetch('/api/documents/stats/', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }),
          fetch('/api/chat/stats/', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }),
          fetch('/api/chat/activity-chart/', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
        ]);

        // Log de erros de API se necessário
        if (!documentsRes.ok) console.error('Erro na API de documentos:', documentsRes.status);
        if (!chatRes.ok) console.error('Erro na API de chat:', chatRes.status);
        if (!activityRes.ok) console.error('Erro na API de atividade:', activityRes.status);

        // Processar respostas
        const documentsData = documentsRes.ok ? await documentsRes.json() : {};
        const chatData = chatRes.ok ? await chatRes.json() : {};
        const activityDataRes = activityRes.ok ? await activityRes.json() : [];
        
        // Tratar erros da API de atividade
        if (!activityRes.ok) {
          const errorText = await activityRes.text();
          console.error('DashboardPage - activity endpoint error:', errorText);
        }

        // Calcular estatísticas dinâmicas
        const totalDocuments = documentsData.total_documents || 0;
        const totalChats = chatData.total_sessions || 0;
        const totalMessages = chatData.total_messages || 0;
        const avgResponseTime = (chatData.avg_response_time || 0) / 1000; // Converter para segundos

        setStats({
          totalChats: totalChats, // Total de conversas (sessões)
          totalDocuments: totalDocuments,
          totalDownloads: 0, // TODO: Implementar endpoint de downloads
          activeUsers: 1, // Por enquanto assumir usuário atual
          avgResponseTime: parseFloat(avgResponseTime.toFixed(1)),
          systemUptime: 99.8 // TODO: Implementar monitoramento real
        });

        // Definir dados do gráfico de atividade
        setActivityData(activityDataRes);
      } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
        setError('Erro ao carregar dados do dashboard');
        // Fallback para dados padrão em caso de erro
        setStats({
          totalChats: 0,
          totalDocuments: 0,
          totalDownloads: 0,
          activeUsers: 1,
          avgResponseTime: 0,
          systemUptime: 99.8
        });
      }
      
      setLoading(false);
    };

    loadStats();
  }, []);

  const handleNewChat = () => {
    navigate('/chat');
  };

  const handleDocuments = () => {
    navigate('/documents');
  };

  const handleDownloads = () => {
    // TODO: Implementar página de downloads
    alert('Funcionalidade de Downloads será implementada em breve');
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="h-full flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-accent" />
            <p className="text-muted-foreground">Carregando dashboard...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="h-full overflow-y-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-4 sm:py-6 space-y-4 sm:space-y-6">
          {/* Header */}
          <div className="flex flex-col space-y-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground">
              Visão geral do Knight Agent - Seu assistente IA corporativo
            </p>
            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 rounded-lg text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Quick Actions Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
            <Card 
              className="p-4 sm:p-6 cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-[1.02] group bg-gradient-to-br from-card to-card/50 border border-border hover:border-accent/50"
              onClick={handleNewChat}
            >
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
                  <MessageSquare className="h-6 w-6 text-accent" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-card-foreground group-hover:text-accent transition-colors">
                    Novo Chat
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Converse com o Knight
                  </p>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-accent transition-colors" />
              </div>
            </Card>

            <Card 
              className="p-4 sm:p-6 cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-[1.02] group bg-gradient-to-br from-card to-card/50 border border-border hover:border-accent/50"
              onClick={handleDocuments}
            >
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
                  <FileText className="h-6 w-6 text-accent" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-card-foreground group-hover:text-accent transition-colors">
                    Documentos
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Gerenciar conhecimento
                  </p>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-accent transition-colors" />
              </div>
            </Card>

            <Card 
              className="p-4 sm:p-6 cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-[1.02] group bg-gradient-to-br from-card to-card/50 border border-border hover:border-accent/50"
              onClick={handleDownloads}
            >
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
                  <Download className="h-6 w-6 text-accent" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-card-foreground group-hover:text-accent transition-colors">
                    Downloads
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Arquivos temporários
                  </p>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-accent transition-colors" />
              </div>
            </Card>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
              <div className="flex items-center justify-between relative z-10">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total de conversas</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.totalChats.toLocaleString()}</p>
                </div>
                <div className="relative -mt-5">
                  <MessageSquare className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                    style={{
                      '--hover-color': 'rgb(var(--card-hover-icon))'
                    } as React.CSSProperties}
                    onMouseEnter={(e) => {
                      (e.target as HTMLElement).style.color = 'var(--hover-color)';
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLElement).style.color = '';
                    }}
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm relative z-10">
                <TrendingUp className="h-4 w-4 text-accent mr-1" />
                <span className="text-accent">Ativo</span>
                <span className="text-muted-foreground ml-1">mensagens trocadas</span>
              </div>
              
              {/* Shine Effect */}
              <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                     style={{
                       background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                     }}>
                </div>
              </div>
              
              {/* Animated Background */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                   style={{
                     maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                     WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                   }}>
                
                {/* Animated Tiles */}
                <div className="absolute inset-0">
                  <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.05)',
                    animation: 'randomPulse 3.2s ease-in-out infinite',
                    animationDelay: '0s'
                  }}></div>
                  <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.08)',
                    animation: 'randomPulse 2.8s ease-in-out infinite',
                    animationDelay: '0.9s'
                  }}></div>
                  <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.03)',
                    animation: 'randomPulse 3.5s ease-in-out infinite',
                    animationDelay: '1.8s'
                  }}></div>
                  <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.12)',
                    animation: 'randomPulse 2.3s ease-in-out infinite',
                    animationDelay: '2.1s'
                  }}></div>
                  <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.06)',
                    animation: 'randomPulse 4.1s ease-in-out infinite',
                    animationDelay: '0.4s'
                  }}></div>
                  <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.11)',
                    animation: 'randomPulse 2.7s ease-in-out infinite',
                    animationDelay: '1.3s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.04)',
                    animation: 'randomPulse 3.8s ease-in-out infinite',
                    animationDelay: '2.7s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.09)',
                    animation: 'randomPulse 3.1s ease-in-out infinite',
                    animationDelay: '1.6s'
                  }}></div>
                </div>
                
                {/* Animated Lines */}
                <div className="absolute inset-0">
                  <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                  <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                </div>
              </div>
            </Card>

            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
              <div className="flex items-center justify-between relative z-10">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Documentos ativos</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.totalDocuments}</p>
                </div>
                <div className="relative -mt-5">
                  <FileText className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                    style={{
                      '--hover-color': 'rgb(var(--card-hover-icon))'
                    } as React.CSSProperties}
                    onMouseEnter={(e) => {
                      (e.target as HTMLElement).style.color = 'var(--hover-color)';
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLElement).style.color = '';
                    }}
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm relative z-10">
                <TrendingUp className="h-4 w-4 text-accent mr-1" />
                <span className="text-accent">Disponível</span>
                <span className="text-muted-foreground ml-1">base de conhecimento</span>
              </div>
              
              {/* Shine Effect */}
              <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                     style={{
                       background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                     }}>
                </div>
              </div>
              
              {/* Animated Background */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                   style={{
                     maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                     WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                   }}>
                
                {/* Animated Tiles */}
                <div className="absolute inset-0">
                  <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.04)',
                    animation: 'randomPulse 3.4s ease-in-out infinite',
                    animationDelay: '0.3s'
                  }}></div>
                  <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.09)',
                    animation: 'randomPulse 2.9s ease-in-out infinite',
                    animationDelay: '1.1s'
                  }}></div>
                  <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.07)',
                    animation: 'randomPulse 3.7s ease-in-out infinite',
                    animationDelay: '2.0s'
                  }}></div>
                  <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.11)',
                    animation: 'randomPulse 2.5s ease-in-out infinite',
                    animationDelay: '0.7s'
                  }}></div>
                  <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.05)',
                    animation: 'randomPulse 4.2s ease-in-out infinite',
                    animationDelay: '1.9s'
                  }}></div>
                  <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.08)',
                    animation: 'randomPulse 3.0s ease-in-out infinite',
                    animationDelay: '0.5s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.06)',
                    animation: 'randomPulse 3.6s ease-in-out infinite',
                    animationDelay: '1.4s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.10)',
                    animation: 'randomPulse 2.6s ease-in-out infinite',
                    animationDelay: '2.3s'
                  }}></div>
                </div>
                
                {/* Animated Lines */}
                <div className="absolute inset-0">
                  <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                  <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                </div>
              </div>
            </Card>

            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
              <div className="flex items-center justify-between relative z-10">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Usuários ativos</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.activeUsers}</p>
                </div>
                <div className="relative -mt-5">
                  <Users className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                    style={{
                      '--hover-color': 'rgb(var(--card-hover-icon))'
                    } as React.CSSProperties}
                    onMouseEnter={(e) => {
                      (e.target as HTMLElement).style.color = 'var(--hover-color)';
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLElement).style.color = '';
                    }}
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm relative z-10">
                <TrendingUp className="h-4 w-4 text-accent mr-1" />
                <span className="text-accent">Online</span>
                <span className="text-muted-foreground ml-1">sessão ativa</span>
              </div>
              
              {/* Shine Effect */}
              <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                     style={{
                       background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                     }}>
                </div>
              </div>
              
              {/* Animated Background */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                   style={{
                     maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                     WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                   }}>
                
                {/* Animated Tiles */}
                <div className="absolute inset-0">
                  <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.08)',
                    animation: 'randomPulse 2.8s ease-in-out infinite',
                    animationDelay: '0.6s'
                  }}></div>
                  <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.04)',
                    animation: 'randomPulse 3.5s ease-in-out infinite',
                    animationDelay: '1.4s'
                  }}></div>
                  <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.10)',
                    animation: 'randomPulse 4.0s ease-in-out infinite',
                    animationDelay: '0.2s'
                  }}></div>
                  <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.06)',
                    animation: 'randomPulse 3.2s ease-in-out infinite',
                    animationDelay: '2.4s'
                  }}></div>
                  <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.11)',
                    animation: 'randomPulse 2.4s ease-in-out infinite',
                    animationDelay: '0.9s'
                  }}></div>
                  <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.05)',
                    animation: 'randomPulse 3.8s ease-in-out infinite',
                    animationDelay: '1.7s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.09)',
                    animation: 'randomPulse 2.7s ease-in-out infinite',
                    animationDelay: '1.1s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.07)',
                    animation: 'randomPulse 3.9s ease-in-out infinite',
                    animationDelay: '2.6s'
                  }}></div>
                </div>
                
                {/* Animated Lines */}
                <div className="absolute inset-0">
                  <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                  <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                </div>
              </div>
            </Card>

            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border relative group cursor-pointer transition-all duration-300 hover:shadow-xl overflow-hidden">
              <div className="flex items-center justify-between relative z-10">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Tempo de resposta</p>
                  <p className="text-2xl font-bold text-foreground">{stats?.avgResponseTime}s</p>
                </div>
                <div className="relative -mt-5">
                  <Clock className="h-8 w-8 text-accent transition-colors duration-300 relative z-10" 
                    style={{
                      '--hover-color': 'rgb(var(--card-hover-icon))'
                    } as React.CSSProperties}
                    onMouseEnter={(e) => {
                      (e.target as HTMLElement).style.color = 'var(--hover-color)';
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLElement).style.color = '';
                    }}
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center text-sm relative z-10">
                <TrendingUp className="h-4 w-4 text-accent mr-1" />
                <span className="text-accent">Otimizado</span>
                <span className="text-muted-foreground ml-1">performance IA</span>
              </div>
              
              {/* Shine Effect */}
              <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 overflow-hidden">
                <div className="absolute w-[150%] h-[150%] rounded-full left-1/2 bottom-[50%] transform -translate-x-1/2 blur-[35px] opacity-30"
                     style={{
                       background: `conic-gradient(from 205deg at 50% 50%, var(--card-effect-glow))`
                     }}>
                </div>
              </div>
              
              {/* Animated Background */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                   style={{
                     maskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)',
                     WebkitMaskImage: 'radial-gradient(circle at 60% 5%, black 0%, black 15%, transparent 60%)'
                   }}>
                
                {/* Animated Tiles */}
                <div className="absolute inset-0">
                  <div className="absolute top-0 left-0 h-[10%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.07)',
                    animation: 'randomPulse 3.1s ease-in-out infinite',
                    animationDelay: '0.8s'
                  }}></div>
                  <div className="absolute top-0 left-[22.5%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.11)',
                    animation: 'randomPulse 2.6s ease-in-out infinite',
                    animationDelay: '1.6s'
                  }}></div>
                  <div className="absolute top-0 left-[50%] h-[10%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.05)',
                    animation: 'randomPulse 4.3s ease-in-out infinite',
                    animationDelay: '0.1s'
                  }}></div>
                  <div className="absolute top-[10%] left-0 h-[22.5%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.09)',
                    animation: 'randomPulse 3.7s ease-in-out infinite',
                    animationDelay: '2.2s'
                  }}></div>
                  <div className="absolute top-[10%] left-[22.5%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.04)',
                    animation: 'randomPulse 2.9s ease-in-out infinite',
                    animationDelay: '1.0s'
                  }}></div>
                  <div className="absolute top-[10%] left-[50%] h-[22.5%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.12)',
                    animation: 'randomPulse 3.3s ease-in-out infinite',
                    animationDelay: '2.8s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-0 h-[20%] w-[22.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.08)',
                    animation: 'randomPulse 4.1s ease-in-out infinite',
                    animationDelay: '0.4s'
                  }}></div>
                  <div className="absolute top-[32.5%] left-[22.5%] h-[20%] w-[27.5%]" style={{
                    background: 'rgb(var(--card-effect-primary) / 0.06)',
                    animation: 'randomPulse 2.4s ease-in-out infinite',
                    animationDelay: '1.8s'
                  }}></div>
                </div>
                
                {/* Animated Lines */}
                <div className="absolute inset-0">
                  <div className="absolute top-[10%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-0 bottom-0 left-[22.5%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-75"></div>
                  <div className="absolute top-[32.5%] left-0 right-0 h-px bg-accent/40 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300 delay-150"></div>
                  <div className="absolute top-0 bottom-0 left-[50%] w-px bg-accent/40 origin-top scale-y-0 group-hover:scale-y-100 transition-transform duration-300 delay-150"></div>
                </div>
              </div>
            </Card>
          </div>

          {/* Chart Section */}
          <div className="w-full">
            <ChartAreaInteractive 
              data={activityData && activityData.length > 0 ? activityData : null}
              title="Atividade do Knight Agent"
              description="Conversas iniciadas e documentos consultados"
            />
          </div>

          {/* Performance Cards */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-6">
            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Desempenho do Sistema</h3>
                <Activity className="h-5 w-5 text-accent" />
              </div>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Uptime</span>
                    <span className="font-medium text-foreground">{stats?.systemUptime}%</span>
                  </div>
                  <Progress value={stats?.systemUptime} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Processamento RAG</span>
                    <span className="font-medium text-foreground">94%</span>
                  </div>
                  <Progress value={94} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Satisfação dos Usuários</span>
                    <span className="font-medium text-foreground">92%</span>
                  </div>
                  <Progress value={92} className="h-2" />
                </div>
              </div>
            </Card>

            <Card className="p-4 sm:p-6 bg-gradient-to-br from-card to-card/45 border border-border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Atividade Recente</h3>
                <BarChart3 className="h-5 w-5 text-accent" />
              </div>
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-green-500"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Nova conversa iniciada</p>
                    <p className="text-xs text-muted-foreground">há 2 minutos</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Documento processado</p>
                    <p className="text-xs text-muted-foreground">há 15 minutos</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Download solicitado</p>
                    <p className="text-xs text-muted-foreground">há 1 hora</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Usuário conectado</p>
                    <p className="text-xs text-muted-foreground">há 2 horas</p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};