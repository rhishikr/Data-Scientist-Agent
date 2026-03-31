import React, { useMemo, useState } from "react";
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
  ChevronDown,
  ChevronUp,
  Lightbulb,
  CheckCircle,
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
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";
import { ChartNarrative } from "../charts/ChartNarrative";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const COLLAPSED_ROW_COUNT = 10;

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

const genderChartConfig = {
  count: { label: "Customers" },
} satisfies ChartConfig;

const ageGroupChartConfig = {
  count: {
    label: "Customers",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig;

const GENDER_COLORS: Record<string, string> = {
  Female: "var(--chart-1)",
  Male: "var(--chart-2)",
  "Non-binary": "var(--chart-4)",
  "Prefer not to say": "var(--chart-3)",
};

const LOYALTY_COLORS: Record<string, string> = {
  bronze: "#CD7F32",
  silver: "#9CA3AF",
  gold: "#F59E0B",
  platinum: "#6366F1",
};

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

const BUCKET_LABELS = [
  "Very Low",
  "Low",
  "Moderate",
  "High",
  "Very High",
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
  chartNarrative?: ChartNarrativeData | null;
  segmentRecommendations?: Record<string, string[]> | null;
  snapshot?: Snapshot | null;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function CustomersTab({
  cards,
  customers,
  churnPredictions,
  chartNarrative,
  segmentRecommendations,
  snapshot,
}: CustomersTabProps) {
  const [showAllAtRisk, setShowAllAtRisk] = useState(false);
  const [showAllTopBuyers, setShowAllTopBuyers] = useState(false);

  /* ---------- KPI values ---------- */
  const active30d = getCardValue(cards, "active_customers_30d");
  const new30d = getCardValue(cards, "new_customers_30d");
  const returning = getCardValue(cards, "returning_customers_30d");
  const avgClv = getCardValue(cards, "avg_clv");
  const churnRate = getCardValue(cards, "churn_rate_proxy");
  const retentionRate = getCardValue(cards, "retention_rate_proxy");

  /* ---------- Demographics data ---------- */
  const demographics = snapshot?.kpis?.demographics;

  const genderData = useMemo(() => {
    const raw = demographics?.customers_by_gender;
    if (!raw) return [];
    return Object.entries(raw).map(([name, value]) => ({
      name,
      value: safeNum(value),
      fill: GENDER_COLORS[name] ?? "var(--chart-5)",
    }));
  }, [demographics]);

  const ageGroupData = useMemo(() => {
    const raw = demographics?.customers_by_age_group;
    if (!raw) return [];
    return Object.entries(raw).map(([group, count]) => ({
      group,
      count: safeNum(count),
    }));
  }, [demographics]);

  const loyaltyData = useMemo(() => {
    const tiers = demographics?.customers_by_loyalty_tier;
    const spends = demographics?.avg_spend_by_loyalty;
    if (!tiers) return [];
    const total = Object.values(tiers).reduce((s: number, v: any) => s + safeNum(v), 0);
    return Object.entries(tiers).map(([tier, count]) => ({
      tier: tier.charAt(0).toUpperCase() + tier.slice(1),
      tierKey: tier,
      count: safeNum(count),
      pct: total > 0 ? Math.round((safeNum(count) / total) * 100) : 0,
      avgSpend: spends?.[tier] != null ? safeNum(spends[tier]) : null,
      fill: LOYALTY_COLORS[tier] ?? "var(--chart-5)",
    }));
  }, [demographics]);

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
      { range: "0-20%", label: BUCKET_LABELS[0], min: 0, max: 0.2, count: 0 },
      { range: "20-40%", label: BUCKET_LABELS[1], min: 0.2, max: 0.4, count: 0 },
      { range: "40-60%", label: BUCKET_LABELS[2], min: 0.4, max: 0.6, count: 0 },
      { range: "60-80%", label: BUCKET_LABELS[3], min: 0.6, max: 0.8, count: 0 },
      { range: "80-100%", label: BUCKET_LABELS[4], min: 0.8, max: 1.01, count: 0 },
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
      range: `${b.label}\n(${b.range})`,
      count: b.count,
      fill: BUCKET_COLORS[i],
    }));
  }, [churnPredictions]);

  /* ---------- Churn risk summary stats ---------- */
  const churnSummary = useMemo(() => {
    const highRisk = churnPredictions.filter((cp) => safeNum(cp.churn_prob_30d) >= 0.6);
    const totalSpendAtRisk = highRisk.reduce((sum, cp) => sum + safeNum(cp.total_spend), 0);
    const pct = churnPredictions.length > 0
      ? Math.round((highRisk.length / churnPredictions.length) * 100)
      : 0;
    return { count: highRisk.length, spend: totalSpendAtRisk, pct };
  }, [churnPredictions]);

  /* ---------- At-Risk Customers (top 20) ---------- */
  const atRiskCustomers = useMemo(() => {
    return [...churnPredictions]
      .sort((a, b) => b.churn_prob_30d - a.churn_prob_30d)
      .slice(0, 20);
  }, [churnPredictions]);

  /* ---------- Top Buyers ---------- */
  const topBuyers = useMemo(() => {
    return [...churnPredictions]
      .filter((cp) => cp.segment === "Top Buyer")
      .sort((a, b) => safeNum(b.total_spend) - safeNum(a.total_spend))
      .slice(0, 20);
  }, [churnPredictions]);

  const visibleAtRisk = showAllAtRisk ? atRiskCustomers : atRiskCustomers.slice(0, COLLAPSED_ROW_COUNT);
  const visibleTopBuyers = showAllTopBuyers ? topBuyers : topBuyers.slice(0, COLLAPSED_ROW_COUNT);

  return (
    <div className="space-y-6">
      {/* Chart Narrative */}
      {chartNarrative && (
        <ChartNarrative narrative={chartNarrative.narrative} actionHint={chartNarrative.action_hint} />
      )}

      {/* ============================================================
          Row 1: 6 KPI cards
          ============================================================ */}
      <div className="flex rounded-md border bg-card text-card-foreground">
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
          Row 1b: Demographics (Gender + Age Group + Loyalty)
          ============================================================ */}
      {(genderData.length > 0 || ageGroupData.length > 0 || loyaltyData.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Gender Distribution Donut */}
          {genderData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Gender Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartEnlargeWrapper title="Gender Distribution">
                  <ChartContainer config={genderChartConfig} className="w-full" style={{ height: 220 }}>
                    <PieChart>
                      <ChartTooltip
                        content={
                          <ChartTooltipContent
                            formatter={(value, name) => (
                              <span>
                                {name}: {Number(value).toLocaleString()}
                              </span>
                            )}
                          />
                        }
                      />
                      <Pie
                        data={genderData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={45}
                        outerRadius={80}
                        paddingAngle={3}
                        strokeWidth={2}
                        label={({ value }) => `${value}`}
                      >
                        {genderData.map((entry) => (
                          <Cell key={entry.name} fill={entry.fill} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ChartContainer>
                  <div className="flex flex-wrap gap-3 mt-3 justify-center">
                    {genderData.map((g) => (
                      <div key={g.name} className="flex items-center gap-1.5 text-xs">
                        <span
                          className="rounded-sm shrink-0 inline-block"
                          style={{ backgroundColor: g.fill, width: 12, height: 12 }}
                        />
                        <span className="text-muted-foreground">
                          {g.name} ({g.value})
                        </span>
                      </div>
                    ))}
                  </div>
                </ChartEnlargeWrapper>
              </CardContent>
            </Card>
          )}

          {/* Age Group Horizontal Bar */}
          {ageGroupData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Age Group Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartEnlargeWrapper title="Age Group Distribution">
                  <ChartContainer config={ageGroupChartConfig} className="w-full" style={{ height: 220 }}>
                    <BarChart
                      data={ageGroupData}
                      layout="vertical"
                      margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="group"
                        tick={{ fontSize: 11 }}
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
                      <Bar
                        dataKey="count"
                        fill="var(--chart-2)"
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ChartContainer>
                </ChartEnlargeWrapper>
              </CardContent>
            </Card>
          )}

          {/* Loyalty Tier Breakdown */}
          {loyaltyData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Loyalty Tiers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Stacked bar visualization */}
                <div className="flex h-6 rounded-md overflow-hidden">
                  {loyaltyData.map((tier) => (
                    <div
                      key={tier.tierKey}
                      className="relative group"
                      style={{
                        width: `${tier.pct}%`,
                        backgroundColor: tier.fill,
                        minWidth: tier.pct > 0 ? 4 : 0,
                      }}
                      title={`${tier.tier}: ${tier.count} (${tier.pct}%)`}
                    />
                  ))}
                </div>

                {/* Tier details */}
                <div className="space-y-2.5">
                  {loyaltyData.map((tier) => (
                    <div key={tier.tierKey} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className="rounded-sm shrink-0 inline-block"
                          style={{ backgroundColor: tier.fill, width: 12, height: 12 }}
                        />
                        <span className="font-medium">{tier.tier}</span>
                        <span className="text-muted-foreground text-xs">
                          {tier.count.toLocaleString()} ({tier.pct}%)
                        </span>
                      </div>
                      {tier.avgSpend != null && (
                        <span className="text-xs text-muted-foreground tabular-nums">
                          Avg {fmtCurrency(tier.avgSpend)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ============================================================
          Row 2: Segments Donut + Churn Distribution (with summary)
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

        {/* Churn Risk Distribution Histogram — with summary card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Churn Risk Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Churn risk summary */}
            {churnPredictions.length > 0 && (
              <div className={`rounded-md border p-3 ${
                churnSummary.pct >= 30 ? "border-red-200 bg-red-50" :
                churnSummary.pct >= 15 ? "border-orange-200 bg-orange-50" :
                "border-green-200 bg-green-50"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle className={`size-4 ${
                    churnSummary.pct >= 30 ? "text-red-600" :
                    churnSummary.pct >= 15 ? "text-orange-600" :
                    "text-green-600"
                  }`} />
                  <span className="text-sm font-semibold">
                    {churnSummary.count} customers at high risk ({churnSummary.pct}%)
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {fmtCurrency2(churnSummary.spend)} total spend at risk of churning in the next 30 days
                </p>
              </div>
            )}

            {churnPredictions.length === 0 ? (
              <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
                No churn data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Churn Risk Distribution">
                <ChartContainer config={churnDistConfig} className="w-full" style={{ height: 240 }}>
                  <BarChart
                    data={churnBuckets}
                    margin={{ top: 8, right: 12, bottom: 0, left: 12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="range"
                      tick={{ fontSize: 11 }}
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
          Row 3: Segment Strategy Recommendations
          ============================================================ */}
      {segmentRecommendations && Object.keys(segmentRecommendations).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(["Top Buyer", "Moderate", "At-Risk"] as const).map((seg) => {
            const recs = segmentRecommendations[seg];
            if (!recs || recs.length === 0) return null;

            const config: Record<string, { color: string; borderColor: string; icon: string }> = {
              "Top Buyer": { color: "text-green-700", borderColor: "border-green-200", icon: "bg-green-50" },
              "Moderate": { color: "text-blue-700", borderColor: "border-blue-200", icon: "bg-blue-50" },
              "At-Risk": { color: "text-red-700", borderColor: "border-red-200", icon: "bg-red-50" },
            };
            const cfg = config[seg] ?? config["Moderate"];

            return (
              <Card key={seg} className={`border ${cfg.borderColor}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <div className={`rounded-md p-1.5 ${cfg.icon}`}>
                      <Lightbulb className={`size-4 ${cfg.color}`} />
                    </div>
                    <CardTitle className={`text-sm ${cfg.color}`}>{seg} Strategy</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {recs.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <CheckCircle className={`size-3.5 mt-0.5 shrink-0 ${cfg.color}`} />
                        <span className="text-xs leading-relaxed text-muted-foreground">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* ============================================================
          Row 4: Top Buyers Table
          ============================================================ */}
      {topBuyers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Buyers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead className="text-right">Total Spend</TableHead>
                    <TableHead className="text-right">Orders</TableHead>
                    <TableHead className="text-right">Recency</TableHead>
                    <TableHead>Churn Risk</TableHead>
                    <TableHead>Segment</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleTopBuyers.map((cp) => {
                    const churnPct = Math.round(cp.churn_prob_30d * 100);
                    return (
                      <TableRow key={cp.customer_id}>
                        <TableCell className="font-medium">
                          {cp.name ?? cp.customer_id}
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.total_spend != null ? fmtCurrency2(cp.total_spend) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.total_orders != null ? cp.total_orders.toLocaleString() : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {cp.recency_days != null ? `${cp.recency_days}d` : "-"}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 min-w-[120px]">
                            <Progress
                              value={churnPct}
                              className={`h-2 w-16 ${churnPct >= 60 ? "[&>[data-slot=progress-indicator]]:bg-red-500" : churnPct >= 30 ? "[&>[data-slot=progress-indicator]]:bg-orange-400" : "[&>[data-slot=progress-indicator]]:bg-green-500"}`}
                            />
                            <span className="text-xs font-medium tabular-nums">
                              {churnPct}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge color="green">Top Buyer</Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {topBuyers.length > COLLAPSED_ROW_COUNT && (
              <div className="mt-3 text-center">
                <button
                  type="button"
                  onClick={() => setShowAllTopBuyers((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                >
                  {showAllTopBuyers ? (
                    <>
                      <ChevronUp className="size-3.5" />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="size-3.5" />
                      Show all {topBuyers.length} top buyers
                    </>
                  )}
                </button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ============================================================
          Row 5: At-Risk Customers Table
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
            <>
              <div className="overflow-x-auto">
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
                    {visibleAtRisk.map((cp) => {
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
                              <Badge
                                color={
                                  cp.segment === "Top Buyer"
                                    ? "green"
                                    : cp.segment === "At-Risk"
                                      ? "red"
                                      : cp.segment === "Moderate"
                                        ? "blue"
                                        : "gray"
                                }
                              >
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
              {atRiskCustomers.length > COLLAPSED_ROW_COUNT && (
                <div className="mt-3 text-center">
                  <button
                    type="button"
                    onClick={() => setShowAllAtRisk((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                  >
                    {showAllAtRisk ? (
                      <>
                        <ChevronUp className="size-3.5" />
                        Show less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="size-3.5" />
                        Show all {atRiskCustomers.length} at-risk customers
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
