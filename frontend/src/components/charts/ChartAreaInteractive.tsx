"use client"

import * as React from "react"
// @ts-ignore
import { Area, AreaChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

import { useIsMobile } from "../../hooks/use-mobile"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "../ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "../ui/toggle-group"

interface ChartAreaInteractiveProps {
  title?: string
  description?: string
  data?: Array<{
    date: string
    conversas: number
    documentos: number
  }> | null
}

// Placeholder para dados vazios
const emptyData: Array<{ date: string; conversas: number; documentos: number }> = []

const chartConfig = {
  visitors: {
    label: "Visitantes",
  },
  conversas: {
    label: "Conversas",
    color: "hsl(var(--chart-1))",
  },
  documentos: {
    label: "Documentos", 
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig

export function ChartAreaInteractive({ 
  title = "Atividade do Knight",
  description = "Conversas e consultas de documentos",
  data
}: ChartAreaInteractiveProps) {
  const isMobile = useIsMobile()
  const [timeRange, setTimeRange] = React.useState("30d")

  React.useEffect(() => {
    if (isMobile) {
      setTimeRange("7d")
    }
  }, [isMobile])

  // Usar dados reais se fornecidos, caso contrário array vazio
  const sourceData = data || emptyData
  
  // Se não houver dados, mostrar mensagem apropriada
  if (sourceData.length === 0) {
    return (
      <Card className="@container/card bg-gradient-to-br from-card to-card/45 border border-border">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <p>Carregando dados de atividade...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const filteredData = sourceData.filter((item) => {
    // Corrigir timezone: forçar parsing como data local, não UTC
    const [year, month, day] = item.date.split('-').map(Number)
    const date = new Date(year, month - 1, day) // month é 0-indexed
    
    const referenceDate = new Date()
    let daysToSubtract = 30
    if (timeRange === "30d") {
      daysToSubtract = 30
    } else if (timeRange === "7d") {
      daysToSubtract = 7
    } else if (timeRange === "90d") {
      daysToSubtract = 90
    }
    
    // Garantir que a data de referência está no final do dia para incluir hoje
    const endDate = new Date(referenceDate)
    endDate.setHours(23, 59, 59, 999)
    
    const startDate = new Date(referenceDate)
    startDate.setDate(startDate.getDate() - daysToSubtract)
    startDate.setHours(0, 0, 0, 0)
    
    return date >= startDate && date <= endDate
  })
  

  return (
    <Card className="@container/card bg-gradient-to-br from-card to-card/45 border border-border">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          <span className="hidden @[540px]/card:block">
            {description} - Total dos últimos{" "}
            {timeRange === "30d" ? "30 dias" : timeRange === "7d" ? "7 dias" : "3 meses"}
          </span>
          <span className="@[540px]/card:hidden">
            Últimos {timeRange === "30d" ? "30 dias" : timeRange === "7d" ? "7 dias" : "3 meses"}
          </span>
        </CardDescription>
        <CardAction>
          <ToggleGroup
            type="single"
            value={timeRange}
            onValueChange={(value) => value && setTimeRange(value)}
            variant="outline"
            className="hidden *:data-[slot=toggle-group-item]:!px-4 @[767px]/card:flex"
          >
            <ToggleGroupItem value="90d">3 meses</ToggleGroupItem>
            <ToggleGroupItem value="30d">30 dias</ToggleGroupItem>
            <ToggleGroupItem value="7d">7 dias</ToggleGroupItem>
          </ToggleGroup>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger
              className="flex w-40 @[767px]/card:hidden"
              size="sm"
              aria-label="Selecionar período"
            >
              <SelectValue placeholder="Últimos 30 dias" />
            </SelectTrigger>
            <SelectContent className="rounded-xl bg-card border-border shadow-lg">
              <SelectItem value="90d" className="rounded-lg">
                3 meses
              </SelectItem>
              <SelectItem value="30d" className="rounded-lg">
                30 dias
              </SelectItem>
              <SelectItem value="7d" className="rounded-lg">
                7 dias
              </SelectItem>
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
        {/* Debug: mostrar dados (removido para produção) */}
        {/* <div className="mb-4 text-xs text-muted-foreground">
          Debug: {filteredData.length} pontos de dados | 
          Exemplo: {filteredData[0] ? `${filteredData[0].date}: ${filteredData[0].conversas}/${filteredData[0].documentos}` : 'Sem dados'}
        </div> */}
        
        <div className="w-full h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={filteredData}
              width={undefined}
              height={undefined}
              margin={{
                top: 10,
                right: 40,
                left: 10,
                bottom: 10,
              }}
            >
              <defs>
                <linearGradient id="conversasGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={1} />
                  <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0.1} />
                </linearGradient>
                <linearGradient id="documentosGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--chart-2))" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="hsl(var(--chart-2))" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "rgb(var(--off-white))" }}
                type="category"
                scale="point"
                interval={
                  timeRange === "90d" ? 5 : // 3 meses: pular de 6 em 6 dias
                  timeRange === "30d" ? 1 : // 30 dias: pular de 2 em 2 dias  
                  0 // 7 dias: mostrar todos os dias
                }
                padding={{ left: 10, right: 10 }}
                tickFormatter={(value: any) => {
                  // Corrigir timezone: forçar parsing como data local
                  const [year, month, day] = value.split('-').map(Number)
                  const date = new Date(year, month - 1, day)
                  const formatted = date.toLocaleDateString("pt-BR", {
                    month: "short", // Mês abreviado
                    day: "numeric", // Dia sem zero à esquerda
                  }).replace("de ", "")
                  // Capitalizar primeira letra do mês e remover ponto
                  const parts = formatted.split(" ")
                  if (parts[1]) {
                    parts[1] = parts[1].charAt(0).toUpperCase() + parts[1].slice(1).replace(".", "")
                  }
                  return parts.join(" ")
                }}
              />
              <YAxis 
                axisLine={false}
                tickLine={false}
                tick={false}
              />
              <Tooltip 
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length && label) {
                    // Corrigir timezone: forçar parsing como data local
                    const [year, month, day] = (label as string).split('-').map(Number)
                    const date = new Date(year, month - 1, day)
                    const formattedDate = date.toLocaleDateString("pt-BR", {
                      weekday: "long",
                      day: "numeric", 
                      month: "long"
                    }).replace(" De ", " de ")
                     .replace(/^./, (char) => char.toUpperCase()) // Capitalizar apenas primeira letra
                    
                    return (
                      <div className="bg-gradient-to-b from-muted/90 to-muted/60 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
                        <p className="text-sm font-medium text-muted-foreground mb-2">
                          {formattedDate}
                        </p>
                        {payload.map((entry: any, index: number) => (
                          <div key={index} className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded-full" 
                              style={{ backgroundColor: entry.color }}
                            />
                            <span className="text-sm text-muted-foreground">
                              {entry.name === 'conversas' ? 'Conversas' : 'Documentos'}: 
                            </span>
                            <span className="text-sm font-medium text-foreground">
                              {entry.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Area
                type="monotone"
                dataKey="documentos"
                stackId="1"
                stroke="hsl(var(--chart-2))"
                fill="url(#documentosGradient)"
                strokeWidth={2}
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="conversas"
                stackId="1"
                stroke="hsl(var(--chart-1))"
                fill="url(#conversasGradient)"
                strokeWidth={2}
                connectNulls={false}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}