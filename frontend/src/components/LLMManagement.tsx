import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { useLLMStatusRefresh } from '../hooks/useLLMStatusRefresh';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from './ui/chart';
import { 
  Bot, 
  TestTube, 
  DollarSign, 
  TrendingUp, 
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  BarChart3,
  PieChart
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell } from 'recharts';

interface LLMProvider {
  key: string;
  name: string;
  color: string;
  icon: string;
  description: string;
  is_available: boolean;
  api_key_configured: boolean;
  is_current: boolean;
}

interface LLMMetrics {
  period: {
    start: string;
    end: string;
  };
  summary: {
    total_queries: number;
    successful_queries: number;
    success_rate: number;
    avg_response_time_ms: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
  };
  by_provider: Array<{
    provider: string;
    count: number;
    avg_time: number;
    total_input: number;
    total_output: number;
  }>;
}

interface CostAnalysis {
  costs_by_period: {
    month: PeriodCost;
    '6months': PeriodCost;
    year: PeriodCost;
  };
  projections: {
    next_month: number;
    next_quarter: number;
    next_year: number;
    confidence: string;
    factors: string[];
  };
  provider_comparison: Array<{
    provider: string;
    name: string;
    model: string;
    monthly_cost_usd: number;
    input_cost_per_1k: number;
    output_cost_per_1k: number;
    estimated_savings: number;
  }>;
}

interface PeriodCost {
  period: string;
  total_cost_usd: number;
  daily_average: number;
  breakdown: {
    input_tokens_cost: number;
    output_tokens_cost: number;
  };
}

interface HistoryEntry {
  timestamp: string;
  user: string;
  old_provider: string;
  new_provider: string;
  reason: string;
  provider_names: {
    old: string;
    new: string;
  };
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00'];

export const LLMManagement: React.FC = () => {
  const { user } = useAuth();
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [currentProvider, setCurrentProvider] = useState<LLMProvider | null>(null);
  const [metrics, setMetrics] = useState<LLMMetrics | null>(null);
  const [costs, setCosts] = useState<CostAnalysis | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const { refreshLLMStatus } = useLLMStatusRefresh();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      await Promise.all([
        loadProviders(),
        loadMetrics(),
        loadCosts(),
        loadHistory()
      ]);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedPeriod]);

  useEffect(() => {
    // Só carrega dados se for admin
    if (user?.is_admin) {
      loadData();
    }
  }, [user?.is_admin, loadData]);

  // Só renderiza para administradores
  if (!user?.is_admin) {
    return null;
  }

  const loadProviders = async () => {
    try {
      // Adicionar timestamp para evitar cache
      const timestamp = Date.now();
      const [availableRes, currentRes] = await Promise.all([
        api.get(`/rag/llm/available?t=${timestamp}`),
        api.get(`/rag/llm/current?t=${timestamp}`)
      ]);
      
      setProviders(availableRes.data.providers);
      setCurrentProvider(availableRes.data.providers.find((p: LLMProvider) => p.is_current) || null);
    } catch (error) {
      console.error('Erro ao carregar providers:', error);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await api.get(`/rag/llm/metrics?period=${selectedPeriod}`);
      setMetrics(response.data);
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    }
  };

  const loadCosts = async () => {
    try {
      const response = await api.get('/rag/llm/costs');
      setCosts(response.data);
    } catch (error) {
      console.error('Erro ao carregar custos:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await api.get('/rag/llm/history');
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
    }
  };

  const handleSwitchProvider = async (newProvider: string) => {
    if (!newProvider || newProvider === currentProvider?.key) return;

    try {
      setSwitching(true);

      const response = await api.post('/rag/llm/switch', {
        provider: newProvider,
        test_connection: true,
        reason: 'Switch via admin interface'
      });

      if (response.data.success) {
        // Atualizar estado local imediatamente
        if (providers.length > 0) {
          const updatedProviders = providers.map(p => ({
            ...p,
            is_current: p.key === response.data.new_provider
          }));
          setProviders(updatedProviders);
          setCurrentProvider(updatedProviders.find(p => p.is_current) || null);
        }
        
        // Forçar atualização imediata do header
        await refreshLLMStatus();
        
        // Aguardar um pouco para o backend processar, então recarregar dados
        setTimeout(async () => {
          await loadProviders();
        }, 500);
      }
    } catch (error: any) {
      console.error('Erro ao alternar provider:', error);
    } finally {
      setSwitching(false);
    }
  };

  const handleTestProvider = async (providerKey: string) => {
    try {
      setTesting(providerKey);
      const response = await api.post('/rag/llm/test', { provider: providerKey });
      
      if (response.data.success) {
        console.log(`${providerKey} testado com sucesso (${response.data.response_time_ms}ms)`);
      } else {
        console.error(`Falha no teste: ${response.data.error}`);
      }
    } catch (error: any) {
      console.error('Erro ao testar provider:', error);
    } finally {
      setTesting(null);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR').format(value);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('pt-BR');
  };

  // Preparar dados para gráficos
  const costChartData = costs ? [
    { period: 'Mês', value: costs.costs_by_period.month.total_cost_usd },
    { period: '6 Meses', value: costs.costs_by_period['6months'].total_cost_usd },
    { period: 'Ano', value: costs.costs_by_period.year.total_cost_usd }
  ] : [];

  const providerPieData = costs?.provider_comparison.map((provider, index) => ({
    name: provider.name,
    value: provider.monthly_cost_usd,
    fill: COLORS[index % COLORS.length]
  })) || [];

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <span className="ml-2">Carregando configurações de IA...</span>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="config" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="config">Configuração</TabsTrigger>
          <TabsTrigger value="metrics">Métricas</TabsTrigger>
          <TabsTrigger value="costs">Custos</TabsTrigger>
          <TabsTrigger value="history">Histórico</TabsTrigger>
        </TabsList>

        {/* Aba de Configuração */}
        <TabsContent value="config" className="space-y-4">
          <Card className="p-6">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Selecionar Provider</label>
                <Select
                  value={currentProvider?.key || ''}
                  onValueChange={handleSwitchProvider}
                  disabled={switching}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione um provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((provider) => (
                      <SelectItem 
                        key={provider.key} 
                        value={provider.key}
                        disabled={!provider.is_available}
                        className=""
                      >
                        <div className="flex items-center space-x-2">
                          <span>{provider.name}</span>
                          {!provider.api_key_configured && (
                            <Badge variant="destructive" className="text-xs">Sem API Key</Badge>
                          )}
                          {!provider.is_available && (
                            <Badge variant="secondary" className="text-xs">Indisponível</Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Ações</label>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => currentProvider && handleTestProvider(currentProvider.key)}
                    disabled={!currentProvider || testing === currentProvider.key}
                  >
                    <TestTube className="h-4 w-4 mr-1" />
                    {testing === currentProvider?.key ? 'Testando...' : 'Testar'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadData}
                    disabled={loading}
                  >
                    <Activity className="h-4 w-4 mr-1" />
                    Atualizar
                  </Button>
                </div>
              </div>
            </div>

            {/* Lista de providers disponíveis */}
            <div className="mt-6">
              <h4 className="text-md font-medium mb-3">Providers Disponíveis</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {providers.map((provider) => (
                  <Card key={provider.key} className="p-3 border bg-gray-50 dark:bg-[#181818] shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <img 
                          src={provider.icon} 
                          alt={provider.name}
                          className={`w-5 h-5 object-contain ${(provider.key === 'openai' || provider.key === 'groq') ? 'dark:invert' : ''}`}
                          onError={(e) => {
                            // Fallback para emoji se SVG falhar
                            const target = e.target as HTMLImageElement;
                            target.src = 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><text x="50%" y="50%" font-size="16" text-anchor="middle" dy=".3em">🔧</text></svg>');
                          }}
                        />
                        <div>
                          <p className="font-medium text-sm">{provider.name}</p>
                          <p className="text-xs text-muted-foreground">{provider.description}</p>
                        </div>
                      </div>
                      <div className="flex flex-col space-y-1">
                        {provider.is_current && (
                          <Badge variant="default" className="text-xs">Ativo</Badge>
                        )}
                        {provider.is_available ? (
                          <Badge variant="outline" className="text-xs text-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Online
                          </Badge>
                        ) : (
                          <Badge variant="destructive" className="text-xs">
                            <XCircle className="h-3 w-3 mr-1" />
                            Offline
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => handleTestProvider(provider.key)}
                      disabled={!provider.is_available || testing === provider.key}
                    >
                      {testing === provider.key ? 'Testando...' : 'Testar Conexão'}
                    </Button>
                  </Card>
                ))}
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Aba de Métricas */}
        <TabsContent value="metrics" className="space-y-4">
          {metrics && (
            <>
              {/* KPIs */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Activity className="h-5 w-5 text-blue-500" />
                    <div>
                      <p className="text-sm font-medium">Total de Consultas</p>
                      <p className="text-2xl font-bold">{formatNumber(metrics.summary.total_queries)}</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="text-sm font-medium">Taxa de Sucesso</p>
                      <p className="text-2xl font-bold">{metrics.summary.success_rate}%</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-orange-500" />
                    <div>
                      <p className="text-sm font-medium">Tempo Médio</p>
                      <p className="text-2xl font-bold">{Math.round(metrics.summary.avg_response_time_ms)}ms</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-5 w-5 text-purple-500" />
                    <div>
                      <p className="text-sm font-medium">Custo Estimado</p>
                      <p className="text-2xl font-bold">{formatCurrency(metrics.summary.estimated_cost_usd)}</p>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Métricas por Provider */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Uso por Provider</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Provider</TableHead>
                      <TableHead>Consultas</TableHead>
                      <TableHead>Tempo Médio</TableHead>
                      <TableHead>Tokens Entrada</TableHead>
                      <TableHead>Tokens Saída</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metrics.by_provider.map((provider) => (
                      <TableRow key={provider.provider}>
                        <TableCell className="font-medium">{provider.provider}</TableCell>
                        <TableCell>{formatNumber(provider.count)}</TableCell>
                        <TableCell>{Math.round(provider.avg_time)}ms</TableCell>
                        <TableCell>{formatNumber(provider.total_input || 0)}</TableCell>
                        <TableCell>{formatNumber(provider.total_output || 0)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Aba de Custos */}
        <TabsContent value="costs" className="space-y-4">
          {costs && (
            <>
              {/* Custos por Período */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-4">
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">Este Mês</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs.costs_by_period.month.total_cost_usd)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs.costs_by_period.month.daily_average)}/dia</p>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">6 Meses</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs.costs_by_period['6months'].total_cost_usd)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs.costs_by_period['6months'].daily_average)}/dia</p>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">Anual</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs.costs_by_period.year.total_cost_usd)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs.costs_by_period.year.daily_average)}/dia</p>
                  </div>
                </Card>
              </div>

              {/* Gráficos */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <BarChart3 className="h-5 w-5 mr-2" />
                    Custos por Período
                  </h3>
                  <ChartContainer
                    config={{
                      value: {
                        label: "Custo (USD)",
                        color: "#8884d8"
                      }
                    }}
                    className="h-[300px]"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={costChartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis />
                        <ChartTooltip content={<ChartTooltipContent />} />
                        <Bar dataKey="value" fill="#8884d8" />
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </Card>

                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <PieChart className="h-5 w-5 mr-2" />
                    Custos por Provider
                  </h3>
                  <ChartContainer
                    config={{
                      value: {
                        label: "Custo Mensal (USD)",
                        color: "#82ca9d"
                      }
                    }}
                    className="h-[300px]"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsPieChart>
                        <ChartTooltip content={<ChartTooltipContent />} />
                        <Pie 
                          data={providerPieData} 
                          cx="50%" 
                          cy="50%" 
                          labelLine={false}
                          label={(props: any) => {
                            const { name, percent } = props;
                            return `${name} ${((percent || 0) * 100).toFixed(0)}%`;
                          }}
                          outerRadius={80} 
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {providerPieData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Pie>
                      </RechartsPieChart>
                    </ResponsiveContainer>
                  </ChartContainer>
                </Card>
              </div>

              {/* Projeções */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center">
                  <TrendingUp className="h-5 w-5 mr-2" />
                  Projeções de Custos
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">Próximo Mês</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs.projections.next_month)}</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">Próximo Trimestre</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs.projections.next_quarter)}</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">Próximo Ano</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs.projections.next_year)}</p>
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground">
                    <strong>Confiança:</strong> {costs.projections.confidence}
                  </p>
                  <ul className="text-xs text-muted-foreground mt-2 list-disc list-inside">
                    {costs.projections.factors.map((factor, index) => (
                      <li key={index}>{factor}</li>
                    ))}
                  </ul>
                </div>
              </Card>

              {/* Comparação entre Providers */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Comparação de Custos (Mensal)</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Provider</TableHead>
                      <TableHead>Modelo</TableHead>
                      <TableHead>Custo Mensal</TableHead>
                      <TableHead>Entrada/1k</TableHead>
                      <TableHead>Saída/1k</TableHead>
                      <TableHead>Economia Potencial</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {costs.provider_comparison.map((provider) => (
                      <TableRow key={provider.provider}>
                        <TableCell className="font-medium">{provider.name}</TableCell>
                        <TableCell className="text-xs">{provider.model}</TableCell>
                        <TableCell>{formatCurrency(provider.monthly_cost_usd)}</TableCell>
                        <TableCell>{formatCurrency(provider.input_cost_per_1k)}</TableCell>
                        <TableCell>{formatCurrency(provider.output_cost_per_1k)}</TableCell>
                        <TableCell>
                          {provider.estimated_savings > 0 ? (
                            <span className="text-green-600">
                              {formatCurrency(provider.estimated_savings)}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Aba de Histórico */}
        <TabsContent value="history" className="space-y-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Histórico de Mudanças</h3>
            {history.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data/Hora</TableHead>
                    <TableHead>Usuário</TableHead>
                    <TableHead>Mudança</TableHead>
                    <TableHead>Motivo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((entry, index) => (
                    <TableRow key={index}>
                      <TableCell className="text-sm">
                        {formatDate(entry.timestamp)}
                      </TableCell>
                      <TableCell className="font-medium">
                        {entry.user}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <span className="text-red-600">{entry.provider_names.old}</span>
                          <span>→</span>
                          <span className="text-green-600">{entry.provider_names.new}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {entry.reason}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma mudança registrada
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};