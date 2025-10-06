import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();

  // Definir todas as funções ANTES de loadData para evitar erros de "used before declaration"
  const loadProviders = useCallback(async () => {
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
  }, []);

  const loadMetrics = useCallback(async () => {
    try {
      const response = await api.get(`/rag/llm/metrics?period=${selectedPeriod}`);
      setMetrics(response.data);
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    }
  }, [selectedPeriod]);

  const loadCosts = useCallback(async () => {
    try {
      const response = await api.get('/rag/llm/costs');
      setCosts(response.data);
    } catch (error) {
      console.error('Erro ao carregar custos:', error);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const response = await api.get('/rag/llm/history');
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Erro ao carregar histórico:', error);
    }
  }, []);

  // Agora definir loadData que usa as funções acima
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
  }, [loadProviders, loadMetrics, loadCosts, loadHistory]);

  // useEffect deve vir após todas as definições de hooks
  useEffect(() => {
    // Só carrega dados se for admin
    if (user?.is_admin) {
      loadData();
    }
  }, [user?.is_admin, loadData]);

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

  // Preparar dados para gráficos com validação defensiva
  const costChartData = costs?.costs_by_period ? [
    { period: 'Mês', value: costs.costs_by_period.month?.total_cost_usd || 0 },
    { period: '6 Meses', value: costs.costs_by_period['6months']?.total_cost_usd || 0 },
    { period: 'Ano', value: costs.costs_by_period.year?.total_cost_usd || 0 }
  ] : [];

  const providerPieData = costs?.provider_comparison.map((provider, index) => ({
    name: provider.name,
    value: provider.monthly_cost_usd,
    fill: COLORS[index % COLORS.length]
  })) || [];

  // Verificação de admin após todos os hooks
  if (!user?.is_admin) {
    return null;
  }

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
          <TabsTrigger value="config">{t('llmManagement.config_tab')}</TabsTrigger>
          <TabsTrigger value="metrics">{t('llmManagement.metrics_tab')}</TabsTrigger>
          <TabsTrigger value="costs">{t('llmManagement.costs_tab')}</TabsTrigger>
          <TabsTrigger value="history">{t('llmManagement.history_tab')}</TabsTrigger>
        </TabsList>

        {/* Aba de Configuração */}
        <TabsContent value="config" className="space-y-4">
          <Card className="p-6">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('llmManagement.select_provider')}</label>
                <Select
                  value={currentProvider?.key || ''}
                  onValueChange={handleSwitchProvider}
                  disabled={switching}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('llmManagement.select_provider_placeholder')} />
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
                            <Badge variant="destructive" className="text-xs">{t('llmManagement.no_api_key')}</Badge>
                          )}
                          {!provider.is_available && (
                            <Badge variant="secondary" className="text-xs">{t('llmManagement.unavailable')}</Badge>
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
                    {testing === currentProvider?.key ? t('llmManagement.testing') : t('llmManagement.test')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={loadData}
                    disabled={loading}
                  >
                    <Activity className="h-4 w-4 mr-1" />
                    {t('llmManagement.refresh')}
                  </Button>
                </div>
              </div>
            </div>

            {/* Lista de providers disponíveis */}
            <div className="mt-6">
              <h4 className="text-md font-medium mb-3">{t('llmManagement.available_providers')}</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {providers.map((provider) => (
                  <Card key={provider.key} className="p-4 border bg-gray-50 dark:bg-[#181818] hover:shadow-md transition-shadow duration-200">
                    {/* Layout vertical com melhor hierarquia visual */}
                    <div className="flex flex-col h-full space-y-4">
                      {/* Topo: Logo + Nome (hierarquia primária) */}
                      <div className="flex items-center justify-center space-x-3 pb-3 border-b">
                        <img
                          src={provider.icon}
                          alt={provider.name}
                          className={`w-8 h-8 object-contain ${(provider.key === 'openai' || provider.key === 'groq') ? 'dark:invert' : ''}`}
                          onError={(e) => {
                            // Fallback para ícone emoji quando imagem falhar
                            const target = e.target as HTMLImageElement;
                            target.src = `data:image/svg+xml;base64,${btoa(`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><text x="12" y="18" text-anchor="middle" font-size="18">🤖</text></svg>`)}`
                          }}
                        />
                        <h4 className="font-semibold text-base">{provider.name}</h4>
                      </div>

                      {/* Centro: Status (informação secundária) */}
                      <div className="flex flex-col items-center space-y-2 flex-1">
                        {/* Status de conexão */}
                        <div className="flex items-center justify-center">
                          {provider.is_available ? (
                            <Badge
                              variant="outline"
                              className="px-3 py-1 text-sm border-green-500 bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400"
                            >
                              <CheckCircle className="h-4 w-4 mr-1.5" />
                              {t('llmManagement.online')}
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="px-3 py-1 text-sm border-red-500 bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400"
                            >
                              <XCircle className="h-4 w-4 mr-1.5" />
                              {t('llmManagement.offline')}
                            </Badge>
                          )}
                        </div>

                        {/* Badge de ativo (se aplicável) */}
                        {provider.is_current && (
                          <Badge
                            variant="default"
                            className="px-3 py-1 text-sm bg-primary text-primary-foreground"
                          >
                            {t('llmManagement.active')}
                          </Badge>
                        )}

                        {/* Indicador de configuração de API */}
                        {!provider.api_key_configured && (
                          <p className="text-xs text-muted-foreground text-center">
                            {t('llmManagement.no_api_key')}
                          </p>
                        )}
                      </div>

                      {/* Base: Ação (call-to-action) */}
                      <Button
                        variant={provider.is_available ? "outline" : "ghost"}
                        size="sm"
                        className="w-full transition-colors duration-200"
                        onClick={() => handleTestProvider(provider.key)}
                        disabled={!provider.is_available || testing === provider.key}
                      >
                        <TestTube className="h-4 w-4 mr-1.5" />
                        {testing === provider.key ? t('llmManagement.testing') : t('llmManagement.test_connection')}
                      </Button>
                    </div>
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
                      <p className="text-sm font-medium">{t('llmManagement.total_queries')}</p>
                      <p className="text-2xl font-bold">{formatNumber(metrics.summary.total_queries)}</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="text-sm font-medium">{t('llmManagement.success_rate')}</p>
                      <p className="text-2xl font-bold">{metrics.summary.success_rate}%</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-5 w-5 text-orange-500" />
                    <div>
                      <p className="text-sm font-medium">{t('llmManagement.avg_response_time')}</p>
                      <p className="text-2xl font-bold">{Math.round(metrics.summary.avg_response_time_ms)}ms</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-5 w-5 text-purple-500" />
                    <div>
                      <p className="text-sm font-medium">{t('llmManagement.estimated_cost')}</p>
                      <p className="text-2xl font-bold">{formatCurrency(metrics.summary.estimated_cost_usd)}</p>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Métricas por Provider */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">{t('llmManagement.usage_by_provider')}</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('llmManagement.provider')}</TableHead>
                      <TableHead>{t('llmManagement.queries')}</TableHead>
                      <TableHead>{t('llmManagement.avg_response_time')}</TableHead>
                      <TableHead>{t('llmManagement.input_tokens')}</TableHead>
                      <TableHead>{t('llmManagement.output_tokens')}</TableHead>
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
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.this_month')}</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs?.costs_by_period?.month?.total_cost_usd || 0)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs?.costs_by_period?.month?.daily_average || 0)}/dia</p>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.six_months')}</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs?.costs_by_period?.['6months']?.total_cost_usd || 0)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs?.costs_by_period?.['6months']?.daily_average || 0)}/dia</p>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="text-center">
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.annual')}</p>
                    <p className="text-3xl font-bold">{formatCurrency(costs?.costs_by_period?.year?.total_cost_usd || 0)}</p>
                    <p className="text-xs text-muted-foreground">Média: {formatCurrency(costs?.costs_by_period?.year?.daily_average || 0)}/dia</p>
                  </div>
                </Card>
              </div>

              {/* Gráficos */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center">
                    <BarChart3 className="h-5 w-5 mr-2" />
                    {t('llmManagement.costs_by_period')}
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
                    {t('llmManagement.costs_by_provider')}
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
                  {t('llmManagement.cost_projections')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.next_month')}</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs?.projections?.next_month || 0)}</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.next_quarter')}</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs?.projections?.next_quarter || 0)}</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-sm font-medium text-muted-foreground">{t('llmManagement.next_year')}</p>
                    <p className="text-2xl font-bold">{formatCurrency(costs?.projections?.next_year || 0)}</p>
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground">
                    <strong>{t('llmManagement.confidence')}:</strong> {costs?.projections?.confidence || t('llmManagement.not_available')}
                  </p>
                  <ul className="text-xs text-muted-foreground mt-2 list-disc list-inside">
                    {(costs?.projections?.factors || []).map((factor, index) => (
                      <li key={index}>{factor}</li>
                    ))}
                  </ul>
                </div>
              </Card>

              {/* Comparação entre Providers */}
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">{t('llmManagement.cost_comparison_monthly')}</h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('llmManagement.provider')}</TableHead>
                      <TableHead>{t('llmManagement.model')}</TableHead>
                      <TableHead>{t('llmManagement.monthly_cost')}</TableHead>
                      <TableHead>{t('llmManagement.input_per_1k')}</TableHead>
                      <TableHead>{t('llmManagement.output_per_1k')}</TableHead>
                      <TableHead>{t('llmManagement.potential_savings')}</TableHead>
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
            <h3 className="text-lg font-semibold mb-4">{t('llmManagement.change_history')}</h3>
            {history.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('llmManagement.date_time')}</TableHead>
                    <TableHead>{t('llmManagement.user')}</TableHead>
                    <TableHead>{t('llmManagement.change')}</TableHead>
                    <TableHead>{t('llmManagement.reason')}</TableHead>
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