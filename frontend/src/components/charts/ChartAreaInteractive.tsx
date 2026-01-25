"use client"

import * as React from "react"
// @ts-ignore
import { Area, AreaChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { useTranslation } from "react-i18next"

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
  title,
  description,
  data
}: ChartAreaInteractiveProps) {
  const { t, i18n } = useTranslation()
  const isMobile = useIsMobile()
  const [timeRange, setTimeRange] = React.useState("30d")

  // Get current locale for date formatting
  const currentLocale = i18n.language?.startsWith('pt') ? 'pt-BR' :
                        i18n.language?.startsWith('es') ? 'es-ES' :
                        i18n.language?.startsWith('sv') ? 'sv-SE' : 'en-US'

  // Use translated defaults if not provided
  const displayTitle = title || t('dashboard.knight_activity')
  const displayDescription = description || t('dashboard.conversations_and_documents')

  React.useEffect(() => {
    if (isMobile) {
      setTimeRange("7d")
    }
  }, [isMobile])

  // Use real data if provided, otherwise empty array
  const sourceData = data || emptyData

  // If no data, show appropriate message
  if (sourceData.length === 0) {
    return (
      <Card className="@container/card bg-gradient-to-br from-card to-card/45 border border-border">
        <CardHeader>
          <CardTitle>{displayTitle}</CardTitle>
          <CardDescription>{displayDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <p>{t('dashboard.loading_activity_data')}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const filteredData = sourceData.filter((item) => {
    // Fix timezone: force parsing as local date, not UTC
    const [year, month, day] = item.date.split('-').map(Number)
    const date = new Date(year, month - 1, day) // month is 0-indexed

    const referenceDate = new Date()
    let daysToSubtract = 30
    if (timeRange === "7d") {
      daysToSubtract = 7
    } else if (timeRange === "30d") {
      daysToSubtract = 30
    } else if (timeRange === "90d") {
      daysToSubtract = 90
    } else if (timeRange === "180d") {
      daysToSubtract = 180
    } else if (timeRange === "365d") {
      daysToSubtract = 365
    }

    // Ensure reference date is at end of day to include today
    const endDate = new Date(referenceDate)
    endDate.setHours(23, 59, 59, 999)

    const startDate = new Date(referenceDate)
    startDate.setDate(startDate.getDate() - daysToSubtract)
    startDate.setHours(0, 0, 0, 0)

    return date >= startDate && date <= endDate
  })

  // Helper function to get time range label
  const getTimeRangeLabel = (range: string): string => {
    switch (range) {
      case "7d": return t('dashboard.seven_days')
      case "30d": return t('dashboard.thirty_days')
      case "90d": return t('dashboard.three_months')
      case "180d": return t('dashboard.six_months')
      case "365d": return t('dashboard.one_year')
      default: return t('dashboard.thirty_days')
    }
  }
  

  return (
    <Card className="@container/card bg-gradient-to-br from-card to-card/45 border border-border">
      <CardHeader>
        <CardTitle>{displayTitle}</CardTitle>
        <CardDescription>
          <span className="hidden @[540px]/card:block">
            {displayDescription} - {t('dashboard.total_of_last')} {getTimeRangeLabel(timeRange)}
          </span>
          <span className="@[540px]/card:hidden">
            {getTimeRangeLabel(timeRange)}
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
            <ToggleGroupItem value="365d">{t('dashboard.one_year')}</ToggleGroupItem>
            <ToggleGroupItem value="180d">{t('dashboard.six_months')}</ToggleGroupItem>
            <ToggleGroupItem value="90d">{t('dashboard.three_months')}</ToggleGroupItem>
            <ToggleGroupItem value="30d">{t('dashboard.thirty_days')}</ToggleGroupItem>
            <ToggleGroupItem value="7d">{t('dashboard.seven_days')}</ToggleGroupItem>
          </ToggleGroup>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger
              className="flex w-40 @[767px]/card:hidden"
              size="sm"
              aria-label={t('dashboard.select_period')}
            >
              <SelectValue placeholder={t('dashboard.last_30_days')} />
            </SelectTrigger>
            <SelectContent className="rounded-xl bg-card border-border shadow-lg">
              <SelectItem value="365d" className="rounded-lg">
                {t('dashboard.one_year')}
              </SelectItem>
              <SelectItem value="180d" className="rounded-lg">
                {t('dashboard.six_months')}
              </SelectItem>
              <SelectItem value="90d" className="rounded-lg">
                {t('dashboard.three_months')}
              </SelectItem>
              <SelectItem value="30d" className="rounded-lg">
                {t('dashboard.thirty_days')}
              </SelectItem>
              <SelectItem value="7d" className="rounded-lg">
                {t('dashboard.seven_days')}
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
                  timeRange === "365d" ? 14 : // 1 year: skip every 15 days
                  timeRange === "180d" ? 7 : // 6 months: skip every 8 days
                  timeRange === "90d" ? 5 : // 3 months: skip every 6 days
                  timeRange === "30d" ? 1 : // 30 days: skip every 2 days
                  0 // 7 days: show all days
                }
                padding={{ left: 10, right: 10 }}
                tickFormatter={(value: any) => {
                  // Fix timezone: force parsing as local date
                  const [year, month, day] = value.split('-').map(Number)
                  const date = new Date(year, month - 1, day)
                  return date.toLocaleDateString(currentLocale, {
                    month: "short",
                    day: "numeric",
                  })
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
                    // Fix timezone: force parsing as local date
                    const [year, month, day] = (label as string).split('-').map(Number)
                    const date = new Date(year, month - 1, day)
                    const formattedDate = date.toLocaleDateString(currentLocale, {
                      weekday: "long",
                      day: "numeric",
                      month: "long"
                    })

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
                              {entry.name === 'conversas' ? t('dashboard.conversations') : t('dashboard.documents_consulted')}:
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