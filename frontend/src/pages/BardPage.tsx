import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { FileText, Download, TrendingUp, Award, Calendar, Users } from 'lucide-react';
import { MainLayout } from '../components/MainLayout';
import api from '../services/api';

interface Report {
  id: string;
  report_type: string;
  created_at: string;
  pdf_path: string;
  excel_path?: string;
  data: {
    user_name: string;
    summary: {
      total_courses: number;
      average_score: number;
      certification_rate: number;
      hours_invested: number;
      courses_in_progress: number;
    };
  };
}

interface ReportData {
  report: any;
  files: {
    pdf: string;
    excel: string;
    json: string;
  };
  charts: any;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export function BardPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [recentReport, setRecentReport] = useState<ReportData | null>(null);
  const [activeTab, setActiveTab] = useState('generate');

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await api.get('/bard/reports');
      setReports(response.data.reports || []);
    } catch (error) {
      console.error('Erro ao buscar relatórios:', error);
    }
  };

  const generateReport = async (reportType: string) => {
    setLoading(true);
    try {
      const response = await api.post('/bard/generate-report/', {
        report_type: reportType
      });
      
      setRecentReport(response.data);
      await fetchReports();
      setActiveTab('view');
    } catch (error) {
      console.error('Erro ao gerar relatório:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = (filePath: string, format: string) => {
    const link = document.createElement('a');
    link.href = filePath;
    link.download = `relatorio_${format}_${new Date().getTime()}`;
    link.click();
  };

  const ReportCard = ({ title, description, reportType, variant = 'default' }: {
    title: string;
    description: string;
    reportType: string;
    variant?: 'default' | 'secondary' | 'outline';
  }) => (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="w-5 h-5" />
          {title}
        </CardTitle>
        <CardDescription>
          {description}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button 
          onClick={() => generateReport(reportType)}
          disabled={loading}
          variant={variant}
          className="w-full"
        >
          {loading ? 'Gerando...' : 'Gerar Relatório'}
        </Button>
      </CardContent>
    </Card>
  );

  const ReportsList = () => (
    <div className="space-y-4">
      {reports.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Nenhum relatório gerado ainda</p>
          <p className="text-sm">Gere seu primeiro relatório na aba "Gerar"</p>
        </div>
      ) : (
        reports.map((report) => (
          <Card key={report.id} className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <Badge variant={
                    report.report_type === 'completo' ? 'default' :
                    report.report_type === 'mensal' ? 'secondary' : 'outline'
                  }>
                    {report.report_type}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {new Date(report.created_at).toLocaleDateString('pt-BR')}
                  </span>
                </div>
                <h3 className="font-medium">{report.data.user_name}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-sm">
                  <div className="flex items-center gap-2">
                    <Award className="w-4 h-4 text-blue-500" />
                    <span>{report.data.summary.total_courses} cursos</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-500" />
                    <span>{report.data.summary.average_score}% média</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-purple-500" />
                    <span>{report.data.summary.certification_rate}% cert.</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-orange-500" />
                    <span>{report.data.summary.hours_invested}h investidas</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2 ml-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadReport(report.pdf_path, 'pdf')}
                >
                  <Download className="w-4 h-4 mr-1" />
                  PDF
                </Button>
                {report.excel_path && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadReport(report.excel_path!, 'excel')}
                  >
                    <Download className="w-4 h-4 mr-1" />
                    Excel
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );

  const ReportViewer = () => {
    if (!recentReport) return null;

    const { report } = recentReport;
    const summary = report.summary;

    // Dados para gráficos
    const summaryData = [
      { name: 'Cursos Concluídos', value: summary.total_courses },
      { name: 'Cursos em Andamento', value: summary.courses_in_progress },
      { name: 'Horas Investidas', value: summary.hours_invested },
    ];

    const performanceData = report.completed_courses?.map((course: any) => ({
      name: course.name.length > 20 ? course.name.substring(0, 20) + '...' : course.name,
      score: course.score,
      hours: course.hours || 0,
    })) || [];

    return (
      <div className="space-y-6">
        {/* Cabeçalho do Relatório */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold">{report.user_name}</h2>
              <p className="text-muted-foreground">{report.department} - {report.role}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Relatório gerado em</p>
              <p className="font-medium">{new Date(report.report_date).toLocaleDateString('pt-BR')}</p>
            </div>
          </div>

          {/* Resumo Executivo */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{summary.total_courses}</div>
              <div className="text-sm text-blue-800">Cursos Concluídos</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{summary.average_score}%</div>
              <div className="text-sm text-green-800">Média Geral</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{summary.certification_rate}%</div>
              <div className="text-sm text-purple-800">Taxa Certificação</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{summary.hours_invested}h</div>
              <div className="text-sm text-orange-800">Horas Investidas</div>
            </div>
          </div>
        </Card>

        {/* Gráficos */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico de Performance */}
          <Card className="p-6">
            <CardHeader>
              <CardTitle>Performance por Curso</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="score" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Gráfico de Pizza - Resumo */}
          <Card className="p-6">
            <CardHeader>
              <CardTitle>Distribuição de Atividades</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={summaryData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                    label={(entry) => `${entry.name}: ${entry.value}`}
                  >
                    {summaryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Downloads */}
        <Card className="p-6">
          <CardHeader>
            <CardTitle>Downloads Disponíveis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button onClick={() => downloadReport(recentReport.files.pdf, 'pdf')}>
                <Download className="w-4 h-4 mr-2" />
                Baixar PDF
              </Button>
              <Button variant="outline" onClick={() => downloadReport(recentReport.files.excel, 'excel')}>
                <Download className="w-4 h-4 mr-2" />
                Baixar Excel
              </Button>
              <Button variant="outline" onClick={() => downloadReport(recentReport.files.json, 'json')}>
                <Download className="w-4 h-4 mr-2" />
                Baixar JSON
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <MainLayout 
      title="🎭 Bard"
      subtitle="Central de Relatórios e Análises de Performance"
    >
      <div className="h-full overflow-y-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-8">

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="generate">Gerar Relatórios</TabsTrigger>
            <TabsTrigger value="view">Visualizar</TabsTrigger>
            <TabsTrigger value="history">Histórico</TabsTrigger>
          </TabsList>

          {/* Tab: Gerar Relatórios */}
          <TabsContent value="generate" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ReportCard
                title="Relatório Completo"
                description="Análise detalhada de todas as suas capacitações, performance e certificações"
                reportType="completo"
              />
              
              <ReportCard
                title="Relatório Mensal"
                description="Resumo das atividades e progressos do último mês"
                reportType="mensal"
                variant="secondary"
              />
              
              <ReportCard
                title="Certificações"
                description="Status atual das suas certificações e próximos passos"
                reportType="certificacoes"
                variant="outline"
              />
            </div>

            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
                <div className="flex items-center gap-3">
                  <Award className="w-8 h-8" />
                  <div>
                    <div className="text-2xl font-bold">12</div>
                    <div className="text-blue-100">Cursos Concluídos</div>
                  </div>
                </div>
              </Card>
              
              <Card className="p-4 bg-gradient-to-r from-green-500 to-green-600 text-white">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-8 h-8" />
                  <div>
                    <div className="text-2xl font-bold">85%</div>
                    <div className="text-green-100">Média Geral</div>
                  </div>
                </div>
              </Card>
              
              <Card className="p-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white">
                <div className="flex items-center gap-3">
                  <Users className="w-8 h-8" />
                  <div>
                    <div className="text-2xl font-bold">3</div>
                    <div className="text-purple-100">Em Andamento</div>
                  </div>
                </div>
              </Card>
              
              <Card className="p-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white">
                <div className="flex items-center gap-3">
                  <Calendar className="w-8 h-8" />
                  <div>
                    <div className="text-2xl font-bold">156h</div>
                    <div className="text-orange-100">Horas Investidas</div>
                  </div>
                </div>
              </Card>
            </div>
          </TabsContent>

          {/* Tab: Visualizar */}
          <TabsContent value="view" className="space-y-6">
            {recentReport ? (
              <ReportViewer />
            ) : (
              <Card className="p-12 text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-semibold mb-2">Nenhum relatório para visualizar</h3>
                <p className="text-muted-foreground mb-4">
                  Gere um relatório primeiro para visualizar os dados aqui
                </p>
                <Button onClick={() => setActiveTab('generate')}>
                  Gerar Relatório
                </Button>
              </Card>
            )}
          </TabsContent>

          {/* Tab: Histórico */}
          <TabsContent value="history" className="space-y-6">
            <Card className="p-6">
              <CardHeader>
                <CardTitle>Histórico de Relatórios</CardTitle>
                <CardDescription>
                  Seus relatórios gerados anteriormente
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ReportsList />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        </div>
      </div>
    </MainLayout>
  );
}

export default BardPage;