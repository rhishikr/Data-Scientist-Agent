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
    let topBuyer = 0;
    let moderate = 0;
    let atRisk = 0;

    customers.forEach((c) => {
      const spend = safeNum(c.total_spend);
      if (spend >= 3500) {
        topBuyer++;
      } else if (spend >= 1500) {
        moderate++;
      } else {
        atRisk++;
      }
    });

    return [
      { name: "Top Buyer", value: topBuyer, fill: SEGMENT_COLORS[0] },
      { name: "Moderate", value: moderate, fill: SEGMENT_COLORS[1] },
      { name: "At-Risk", value: atRisk, fill: SEGMENT_COLORS[2] },
    ].filter((s) => s.value > 0);
  }, [customers]);

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
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MiniKpi
          icon={Users}
          label="Active 30d"
          value={Math.round(active30d).toLocaleString()}
          iconColor="text-teal-600"
          iconBg="bg-teal-50"
        />
        <MiniKpi
          icon={UserPlus}
          label="New 30d"
          value={Math.round(new30d).toLocaleString()}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={UserCheck}
          label="Returning"
          value={Math.round(returning).toLocaleString()}
          iconColor="text-green-600"
          iconBg="bg-green-50"
        />
        <MiniKpi
          icon={DollarSign}
          label="Avg CLV"
          value={fmtCurrency(avgClv)}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50"
        />
        <MiniKpi
          icon={AlertTriangle}
          label="Churn Rate"
          value={fmtPercent(churnRate)}
          iconColor="text-orange-600"
          iconBg="bg-orange-50"
        />
        <MiniKpi
          icon={ShieldCheck}
          label="Retention Rate"
          value={fmtPercent(retentionRate)}
          iconColor="text-purple-600"
          iconBg="bg-purple-50"
        />
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
                <ChartContainer config={segmentChartConfig} className="h-[280px] w-full">
                  <PieChart>
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value, name) => (
                            <span>
                              {Number(value).toLocaleString()} customers
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
                    >
                      {segmentData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                  </PieChart>
                </ChartContainer>
                {/* Legend */}
                <div className="flex flex-wrap gap-4 justify-center mt-2">
                  {segmentData.map((seg) => (
                    <div key={seg.name} className="flex items-center gap-1.5 text-xs">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm shrink-0"
                        style={{ backgroundColor: seg.fill }}
                      />
                      <span className="text-muted-foreground">
                        {seg.name} ({seg.value})
                      </span>
                    </div>
                  ))}
                </div>
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
              <ChartContainer config={churnDistConfig} className="h-[280px] w-full">
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
                            <Badge variant="outline" className="text-xs">
                              {cp.segment}
                            </Badge>
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
