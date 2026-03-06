import React, { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  Users,
  UserPlus,
  UserCheck,
  DollarSign,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Progress } from "../../ui/progress";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../../ui/table";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import type {
  KpiCardRow,
  CustomerRow,
  ChurnPrediction,
} from "../dashboard/types";
import {
  fmtCurrency,
  fmtCurrency2,
  fmtPercent,
  getCardValue,
  safeNum,
} from "../dashboard/formatters";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";

/* ------------------------------------------------------------------ */
/* Chart configs                                                       */
/* ------------------------------------------------------------------ */

const segmentChartConfig = {
  count: { label: "Customers" },
} satisfies ChartConfig;

const churnDistConfig = {
  count: {
    label: "Customers",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

/* ------------------------------------------------------------------ */
/* Segment colors                                                      */
/* ------------------------------------------------------------------ */

const SEGMENT_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-4)",
];

/* ------------------------------------------------------------------ */
/* Churn bucket colors (gradient: green low -> orange high)            */
/* ------------------------------------------------------------------ */

const BUCKET_COLORS = [
  "var(--chart-4)", // 0-20%   green-ish
  "var(--chart-3)", // 20-40%
  "var(--chart-2)", // 40-60%
  "var(--chart-5)", // 60-80%
  "var(--chart-1)", // 80-100% orange-ish
];

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
    <Card className="py-2.5 px-3 gap-0">
      <CardContent className="p-0">
        <div className="flex items-center gap-2.5">
          <div className={`rounded-md p-1.5 ${iconBg}`}>
            <Icon className={`size-3.5 ${iconColor}`} />
          </div>
          <div>
            <div className="text-lg font-semibold tracking-tight leading-none">
              {value}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface CustomersTabProps {
  cards: KpiCardRow[];
  customers: CustomerRow[];
  churnPredictions: ChurnPrediction[];
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function CustomersTab({
  cards,
  customers,
  churnPredictions,
}: CustomersTabProps) {
  /* ---------- KPI values ---------- */
  const active30d = getCardValue(cards, "active_customers_30d");
  const new30d = getCardValue(cards, "new_customers_30d");
  const returning = getCardValue(cards, "returning_customers_30d");
  const avgClv = getCardValue(cards, "avg_clv");
  const churnRate = getCardValue(cards, "churn_rate_proxy");
  const retentionRate = getCardValue(cards, "retention_rate_proxy");

  /* ---------- Customer Segments Donut data ---------- */
  const segmentData = useMemo(() => {
    const counts: Record<string, number> = {};

    churnPredictions.forEach((cp) => {
      const seg = cp.segment ?? "Unknown";
      counts[seg] = (counts[seg] || 0) + 1;
    });

    // Fallback to customers array if no churn predictions
    if (Object.keys(counts).length === 0) {
      customers.forEach((c) => {
        const spend = safeNum(c.total_spend);
        const seg = spend >= 3500 ? "Top Buyer" : spend >= 1500 ? "Moderate" : "At-Risk";
        counts[seg] = (counts[seg] || 0) + 1;
      });
    }

    const SEGMENT_COLOR_MAP: Record<string, string> = {
      "Top Buyer": "#22c55e",
      "Moderate": "#eab308",
      "At-Risk": "#ef4444",
    };

    return Object.entries(counts)
      .map(([name, value], i) => ({
        name,
        value,
        fill: SEGMENT_COLOR_MAP[name] ?? SEGMENT_COLORS[i % SEGMENT_COLORS.length],
      }))
      .filter((s) => s.value > 0);
  }, [customers, churnPredictions]);

  /* ---------- Churn Distribution histogram ---------- */
  const churnBuckets = useMemo(() => {
    const buckets = [
      { range: "0-20%", min: 0, max: 0.2, count: 0 },
      { range: "20-40%", min: 0.2, max: 0.4, count: 0 },
      { range: "40-60%", min: 0.4, max: 0.6, count: 0 },
      { range: "60-80%", min: 0.6, max: 0.8, count: 0 },
      { range: "80-100%", min: 0.8, max: 1.01, count: 0 },
    ];

    churnPredictions.forEach((cp) => {
      const prob = safeNum(cp.churn_prob_30d);
      for (const bucket of buckets) {
        if (prob >= bucket.min && prob < bucket.max) {
          bucket.count++;
          break;
        }
      }
    });

    return buckets.map((b, i) => ({
      range: b.range,
      count: b.count,
      fill: BUCKET_COLORS[i],
    }));
  }, [churnPredictions]);

  /* ---------- At-Risk Customers (top 20) ---------- */
  const atRiskCustomers = useMemo(() => {
    return [...churnPredictions]
      .sort((a, b) => b.churn_prob_30d - a.churn_prob_30d)
      .slice(0, 20);
  }, [churnPredictions]);

  return (
    <div className="space-y-6">
      {/* ============================================================
          Row 1: 6 KPI cards
          ============================================================ */}
      <div className="flex rounded-xl border bg-card text-card-foreground">
        {([
          { icon: Users, label: "Active 30d", value: Math.round(active30d).toLocaleString(), color: "text-teal-600" },
          { icon: UserPlus, label: "New 30d", value: Math.round(new30d).toLocaleString(), color: "text-blue-600" },
          { icon: UserCheck, label: "Returning", value: Math.round(returning).toLocaleString(), color: "text-green-600" },
          { icon: DollarSign, label: "Avg CLV", value: fmtCurrency(avgClv), color: "text-emerald-600" },
          { icon: AlertTriangle, label: "Churn Rate", value: fmtPercent(churnRate), color: "text-orange-600" },
          { icon: ShieldCheck, label: "Retention Rate", value: fmtPercent(retentionRate), color: "text-purple-600" },
        ] as const).map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex-1 px-4 py-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-0.5">
                <Icon className={`size-3.5 ${item.color}`} />
                <span className="text-base font-semibold tracking-tight">
                  {item.value}
                </span>
              </div>
              <p className="whitespace-nowrap" style={{ fontSize: 12, lineHeight: 1.2, color: "#6b7280" }}>
                {item.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* ============================================================
          Row 2: Segments Donut + Churn Distribution
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Customer Segments Donut */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Customer Segments</CardTitle>
          </CardHeader>
          <CardContent>
            {segmentData.length === 0 ? (
              <div className="flex items-center justify-center h-[280px] text-sm text-muted-foreground">
                No customer data
              </div>
            ) : (
              <>
                <ChartEnlargeWrapper title="Customer Segments">
                  <ChartContainer config={segmentChartConfig} className="w-full" style={{ height: 280 }}>
                    <PieChart>
                      <ChartTooltip
                        content={
                          <ChartTooltipContent
                            formatter={(value, name) => (
                              <span>
                                {name}: {Number(value).toLocaleString()} customers
                              </span>
                            )}
                          />
                        }
                      />
                      <Pie
                        data={segmentData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={55}
                        outerRadius={95}
                        paddingAngle={3}
                        strokeWidth={2}
                        label={({ value }) => `${value}`}
                      >
                        {segmentData.map((entry) => (
                          <Cell key={entry.name} fill={entry.fill} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ChartContainer>
                  {/* Legend */}
                  <div className="flex flex-wrap gap-3 mt-3 justify-center">
                    {segmentData.map((seg) => (
                      <div key={seg.name} className="flex items-center gap-1.5 text-xs">
                        <span
                          className="rounded-sm shrink-0"
                          style={{
                            backgroundColor: seg.fill,
                            display: "inline-block",
                            width: 12,
                            height: 12,
                            minWidth: 12,
                            minHeight: 12,
                          }}
                        />
                        <span className="text-muted-foreground">
                          {seg.name} ({seg.value})
                        </span>
                      </div>
                    ))}
                  </div>
                </ChartEnlargeWrapper>
              </>
            )}
          </CardContent>
        </Card>

        {/* Churn Risk Distribution Histogram */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Churn Risk Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {churnPredictions.length === 0 ? (
              <div className="flex items-center justify-center h-[280px] text-sm text-muted-foreground">
                No churn data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Churn Risk Distribution">
                <ChartContainer config={churnDistConfig} className="w-full" style={{ height: 280 }}>
                  <BarChart
                    data={churnBuckets}
                    margin={{ top: 8, right: 12, bottom: 0, left: 12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="range"
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                      tickMargin={8}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                      width={40}
                    />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value) =>
                            `${Number(value).toLocaleString()} customers`
                          }
                        />
                      }
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {churnBuckets.map((bucket, idx) => (
                        <Cell key={bucket.range} fill={bucket.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ============================================================
          Row 3: At-Risk Customers Table
          ============================================================ */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">At-Risk Customers</CardTitle>
        </CardHeader>
        <CardContent>
          {atRiskCustomers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No churn prediction data available
            </p>
          ) : (
            <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead>Churn Probability</TableHead>
                    <TableHead className="text-right">Spend</TableHead>
                    <TableHead className="text-right">Recency</TableHead>
                    <TableHead className="text-right">Orders</TableHead>
                    <TableHead>Segment</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {atRiskCustomers.map((cp) => {
                    const churnPct = Math.round(cp.churn_prob_30d * 100);
                    return (
                      <TableRow key={cp.customer_id}>
                        <TableCell className="font-medium">
                          {cp.name ?? cp.customer_id}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 min-w-[140px]">
                            <Progress
                              value={churnPct}
                              className="h-2 w-20 [&>[data-slot=progress-indicator]]:bg-red-500"
                            />
                            <span className="text-xs font-medium tabular-nums">
                              {churnPct}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.total_spend != null
                            ? fmtCurrency2(cp.total_spend)
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.recency_days != null
                            ? `${cp.recency_days}d`
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.total_orders != null
                            ? cp.total_orders.toLocaleString()
                            : "-"}
                        </TableCell>
                        <TableCell>
                          {cp.segment ? (
                            <span
                              className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                                cp.segment === "Top Buyer"
                                  ? "bg-green-100 text-green-800 ring-green-500/30"
                                  : cp.segment === "Moderate"
                                    ? "bg-amber-100 text-amber-800 ring-amber-500/30"
                                    : cp.segment === "At-Risk"
                                      ? "bg-red-100 text-red-800 ring-red-500/30"
                                      : "bg-gray-100 text-gray-800 ring-gray-500/30"
                              }`}
                            >
                              {cp.segment}
                            </span>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
