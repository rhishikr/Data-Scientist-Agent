import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  DollarSign,
  TrendingUp,
  Calendar,
  Target,
  ShoppingCart,
  Hash,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../ui/card";
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
  Snapshot,
} from "../dashboard/types";
import {
  fmtCurrency,
  fmtCurrency2,
  fmtPercent,
  getCardValue,
  safeNum,
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
  snapshot?: Snapshot | null;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

const ORDER_STATUS_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "#8b5cf6",
  "#f59e0b",
  "#06b6d4",
];

const orderStatusChartConfig = {
  count: { label: "Orders" },
} satisfies ChartConfig;

export function RevenueSalesTab({
  cards,
  revenueSeries,
  channelRevenueData,
  forecastSnapshot,
  chartNarrative,
  snapshot,
}: RevenueSalesTabProps) {
  /* ---------- KPI values ---------- */
  const revMtd = getCardValue(cards, "rev_mtd");
  const revQtd = getCardValue(cards, "rev_qtd");
  const revYtd = getCardValue(cards, "rev_ytd");
  const revGrowth30d = getCardValue(cards, "rev_growth_30d");

  /* ---------- Waterfall data ---------- */
  const grossRevenue = getCardValue(cards, "gross_revenue");
  const netRevenue = getCardValue(cards, "net_revenue");
  const totalDiscounts = getCardValue(cards, "total_discounts");
  const totalReturns = getCardValue(cards, "total_returns");
  const totalRefunds = getCardValue(cards, "total_refunds");
  const totalFees = getCardValue(cards, "total_fees");
  const discountRate = getCardValue(cards, "discount_rate");

  const hasWaterfallData = grossRevenue > 0 || netRevenue > 0;

  const waterfallRows = useMemo(() => {
    if (!hasWaterfallData) return [];
    return [
      { label: "Gross Revenue", value: grossRevenue, type: "positive" as const },
      { label: "Discounts", value: -Math.abs(totalDiscounts), type: "negative" as const },
      { label: "Returns", value: -Math.abs(totalReturns), type: "negative" as const },
      { label: "Refunds", value: -Math.abs(totalRefunds), type: "negative" as const },
      { label: "Fees", value: -Math.abs(totalFees), type: "negative" as const },
      { label: "Net Revenue", value: netRevenue, type: "total" as const },
    ];
  }, [grossRevenue, netRevenue, totalDiscounts, totalReturns, totalRefunds, totalFees, hasWaterfallData]);

  /* ---------- AOV + Orders/Day ---------- */
  const aov = getCardValue(cards, "aov");
  const ordersPerDay = getCardValue(cards, "orders_day");

  /* ---------- Order Status Breakdown ---------- */
  const orderStatusBreakdown = useMemo(() => {
    const raw = snapshot?.kpis?.revenue_sales_health?.order_status_breakdown;
    if (!raw || typeof raw !== "object") return [];
    return Object.entries(raw).map(([status, count]) => ({
      status,
      count: safeNum(count, 0),
    }));
  }, [snapshot]);

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
                <div className="flex items-center justify-between rounded-md border p-4">
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
                <div className="flex items-center justify-between rounded-md border p-4">
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
                <div className="flex items-center justify-between rounded-md border p-4">
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
                  <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
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

      {/* ============================================================
          Row 4: AOV + Orders/Day KPI cards
          ============================================================ */}
      <div className="grid grid-cols-2 gap-4">
        <MiniKpi
          icon={ShoppingCart}
          label="Avg Order Value"
          value={fmtCurrency2(aov)}
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
        />
        <MiniKpi
          icon={Hash}
          label="Orders / Day"
          value={ordersPerDay.toLocaleString(undefined, { maximumFractionDigits: 1 })}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50"
        />
      </div>

      {/* ============================================================
          Row 5: Net Revenue Waterfall + Order Status Breakdown
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Net Revenue Waterfall */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Net Revenue Waterfall</CardTitle>
            <CardDescription className="text-xs">
              Gross Revenue to Net Revenue breakdown
              {discountRate > 0 && (
                <span className="ml-2 text-muted-foreground">
                  (Discount rate: {fmtPercent(discountRate)})
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!hasWaterfallData ? (
              <div className="flex items-center justify-center h-[280px] text-sm text-muted-foreground">
                No waterfall data available
              </div>
            ) : (
              <div className="space-y-2">
                {waterfallRows.map((row) => {
                  const maxVal = Math.max(grossRevenue, netRevenue, 1);
                  const barWidth = Math.abs(row.value) / maxVal;
                  return (
                    <div key={row.label} className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground w-28 text-right shrink-0">
                        {row.label}
                      </span>
                      <div className="flex-1 h-7 relative">
                        <div
                          className={`h-full rounded ${
                            row.type === "positive"
                              ? "bg-green-500/80"
                              : row.type === "negative"
                              ? "bg-red-400/70"
                              : "bg-teal-500/80"
                          }`}
                          style={{ width: `${Math.max(barWidth * 100, 2)}%` }}
                        />
                      </div>
                      <span
                        className={`text-sm font-medium w-24 text-right shrink-0 ${
                          row.type === "negative" ? "text-red-600" : ""
                        }`}
                      >
                        {row.type === "negative" ? "-" : ""}
                        {fmtCurrency(Math.abs(row.value))}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Order Status Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Order Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {orderStatusBreakdown.length === 0 ? (
              <div className="flex items-center justify-center h-[280px] text-sm text-muted-foreground">
                No order status data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Order Status Breakdown">
                <ChartContainer config={orderStatusChartConfig} className="w-full" style={{ height: 280 }}>
                  <PieChart>
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value, name) => `${name}: ${Number(value).toLocaleString()}`}
                        />
                      }
                    />
                    <Pie
                      data={orderStatusBreakdown}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={95}
                      paddingAngle={2}
                      label={({ status, percent }) =>
                        `${status} (${(percent * 100).toFixed(0)}%)`
                      }
                      labelLine={false}
                    >
                      {orderStatusBreakdown.map((_, idx) => (
                        <Cell
                          key={idx}
                          fill={ORDER_STATUS_COLORS[idx % ORDER_STATUS_COLORS.length]}
                        />
                      ))}
                    </Pie>
                  </PieChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
