import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  DollarSign,
  TrendingUp,
  Calendar,
  Target,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import type {
  KpiCardRow,
  RevenueForecastPoint,
  ForecastSnapshot,
  ChartNarrativeData,
} from "../dashboard/types";
import {
  fmtCurrency,
  fmtCurrency2,
  fmtPercent,
  getCardValue,
} from "../dashboard/formatters";
import { RevenueLineChart } from "../charts/RevenueLineChart";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";
import { ChartNarrative } from "../charts/ChartNarrative";

/* ------------------------------------------------------------------ */
/* Chart config                                                        */
/* ------------------------------------------------------------------ */

const barChartConfig = {
  revenue: {
    label: "Revenue",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

/* ------------------------------------------------------------------ */
/* Small KPI card component                                            */
/* ------------------------------------------------------------------ */

interface MiniKpiProps {
  icon: React.ElementType;
  label: string;
  value: string;
  iconColor: string;
  iconBg: string;
}

function MiniKpi({ icon: Icon, label, value, iconColor, iconBg }: MiniKpiProps) {
  return (
    <Card className="py-3 px-4 gap-0">
      <CardContent className="p-0">
        <div className="flex items-center gap-2 mb-2">
          <div className={`rounded-md p-1.5 ${iconBg}`}>
            <Icon className={`size-3.5 ${iconColor}`} />
          </div>
        </div>
        <div className="text-xl font-semibold tracking-tight leading-none mb-1">
          {value}
        </div>
        <p className="text-xs text-muted-foreground leading-tight">{label}</p>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface RevenueSalesTabProps {
  cards: KpiCardRow[];
  revenueSeries: RevenueForecastPoint[];
  channelRevenueData: Array<{ channel: string; revenue: number }>;
  forecastSnapshot: ForecastSnapshot | null;
  chartNarrative?: ChartNarrativeData | null;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function RevenueSalesTab({
  cards,
  revenueSeries,
  channelRevenueData,
  forecastSnapshot,
  chartNarrative,
}: RevenueSalesTabProps) {
  /* ---------- KPI values ---------- */
  const revMtd = getCardValue(cards, "rev_mtd");
  const revQtd = getCardValue(cards, "rev_qtd");
  const revYtd = getCardValue(cards, "rev_ytd");
  const revGrowth30d = getCardValue(cards, "rev_growth_30d");

  /* ---------- Forecast summary ---------- */
  const forecasted = forecastSnapshot?.forecasts?.forecasted_revenue;
  const forecast7d = forecasted?.next_7d ?? null;
  const forecast30d = forecasted?.next_30d ?? null;
  const forecast90d = forecasted?.next_90d ?? null;

  return (
    <div className="space-y-6">
      {/* Chart Narrative */}
      {chartNarrative && (
        <ChartNarrative narrative={chartNarrative.narrative} actionHint={chartNarrative.action_hint} />
      )}

      {/* ============================================================
          Row 1: 4 small KPI cards
          ============================================================ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniKpi
          icon={DollarSign}
          label="Revenue MTD"
          value={fmtCurrency(revMtd)}
          iconColor="text-green-600"
          iconBg="bg-green-50"
        />
        <MiniKpi
          icon={Calendar}
          label="Revenue QTD"
          value={fmtCurrency(revQtd)}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={Target}
          label="Revenue YTD"
          value={fmtCurrency(revYtd)}
          iconColor="text-teal-600"
          iconBg="bg-teal-50"
        />
        <MiniKpi
          icon={TrendingUp}
          label="30d Growth"
          value={fmtPercent(revGrowth30d)}
          iconColor="text-purple-600"
          iconBg="bg-purple-50"
        />
      </div>

      {/* ============================================================
          Row 2: Revenue Trend Line Chart (bigger)
          ============================================================ */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Revenue Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <RevenueLineChart data={revenueSeries} height={350} />
        </CardContent>
      </Card>

      {/* ============================================================
          Row 3: Channel Bar Chart + Forecast Summary
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Revenue by Channel Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Revenue by Channel</CardTitle>
          </CardHeader>
          <CardContent>
            {channelRevenueData.length === 0 ? (
              <div className="flex items-center justify-center h-[280px] text-sm text-muted-foreground">
                No channel data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Revenue by Channel">
              <ChartContainer config={barChartConfig} className="w-full" style={{ height: 280 }}>
                <BarChart
                  data={channelRevenueData}
                  margin={{ top: 8, right: 12, bottom: 0, left: 12 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="channel"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                  />
                  <YAxis
                    tickFormatter={(v: number) => fmtCurrency(v)}
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    width={80}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => fmtCurrency(Number(value))}
                      />
                    }
                  />
                  <Bar
                    dataKey="revenue"
                    fill="var(--chart-1)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>

        {/* Forecast Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Forecast Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {forecast7d === null && forecast30d === null && forecast90d === null ? (
              <p className="text-sm text-muted-foreground">
                No forecast data available
              </p>
            ) : (
              <div className="space-y-4">
                {/* 7-day */}
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium">Next 7 Days</p>
                    <p className="text-xs text-muted-foreground">
                      Forecasted revenue
                    </p>
                  </div>
                  <span className="text-lg font-semibold">
                    {forecast7d !== null ? fmtCurrency2(forecast7d) : "N/A"}
                  </span>
                </div>

                {/* 30-day */}
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium">Next 30 Days</p>
                    <p className="text-xs text-muted-foreground">
                      Forecasted revenue
                    </p>
                  </div>
                  <span className="text-lg font-semibold">
                    {forecast30d !== null ? fmtCurrency2(forecast30d) : "N/A"}
                  </span>
                </div>

                {/* 90-day */}
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="text-sm font-medium">Next 90 Days</p>
                    <p className="text-xs text-muted-foreground">
                      Forecasted revenue
                    </p>
                  </div>
                  <span className="text-lg font-semibold">
                    {forecast90d !== null ? fmtCurrency2(forecast90d) : "N/A"}
                  </span>
                </div>

                {/* Model metrics */}
                {forecasted?.metrics && (
                  <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
                    <p>
                      MAE:{" "}
                      <span className="font-medium">
                        {fmtCurrency2(forecasted.metrics.mae ?? 0)}
                      </span>
                    </p>
                    <p>
                      MAPE:{" "}
                      <span className="font-medium">
                        {((forecasted.metrics.mape ?? 0) * 100).toFixed(1)}%
                      </span>
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
