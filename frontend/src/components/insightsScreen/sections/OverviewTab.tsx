import React, { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import {
  AlertTriangle,
  ShieldAlert,
  Heart,
  Lightbulb,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import type {
  KpiCardRow,
  RevenueForecastPoint,
  Insight,
  ForecastSnapshot,
  DemandForecastSku,
} from "../dashboard/types";
import { fmtCurrency } from "../dashboard/formatters";
import { RevenueLineChart } from "../charts/RevenueLineChart";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";

/* ------------------------------------------------------------------ */
/* Chart colors                                                        */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/* Evidence formatter                                                  */
/* ------------------------------------------------------------------ */

function formatEvidence(evidence: unknown): string | null {
  if (!evidence) return null;
  if (typeof evidence === "string") return evidence;
  if (typeof evidence === "object") {
    return Object.entries(evidence as Record<string, unknown>)
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => {
        const label = k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        const val = typeof v === "number" ? (v % 1 !== 0 ? v.toFixed(2) : v) : v;
        return `${label}: ${val}`;
      })
      .join(" · ");
  }
  return String(evidence);
}

const CHANNEL_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

/* ------------------------------------------------------------------ */
/* Severity helpers                                                     */
/* ------------------------------------------------------------------ */

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const SEVERITY_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
};

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface OverviewTabProps {
  cards: KpiCardRow[];
  revenueSeries: RevenueForecastPoint[];
  channelRevenueData: Array<{ channel: string; revenue: number }>;
  insights: Insight[];
  forecastSnapshot: ForecastSnapshot | null;
  demandSkus: DemandForecastSku[];
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function OverviewTab({
  cards,
  revenueSeries,
  channelRevenueData,
  insights,
  forecastSnapshot,
  demandSkus,
}: OverviewTabProps) {
  /* ---------- Stock alert counts ---------- */
  const criticalCount = useMemo(
    () => demandSkus.filter((s) => s.status === "critical").length,
    [demandSkus],
  );
  const warningCount = useMemo(
    () => demandSkus.filter((s) => s.status === "warning").length,
    [demandSkus],
  );

  /* ---------- Top 3 insights by severity ---------- */
  const topInsights = useMemo(() => {
    return [...insights]
      .sort(
        (a, b) =>
          (SEVERITY_ORDER[a.severity] ?? 9) -
          (SEVERITY_ORDER[b.severity] ?? 9),
      )
      .slice(0, 3);
  }, [insights]);

  /* ---------- Risks & Opportunities ---------- */
  const risks =
    forecastSnapshot?.executive_insights?.top_3_risks ?? [];
  const opportunities =
    forecastSnapshot?.executive_insights?.top_3_opportunities ?? [];

  /* ---------- Pie data with fill colors ---------- */
  const pieData = useMemo(
    () =>
      channelRevenueData.map((d, i) => ({
        ...d,
        fill: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
      })),
    [channelRevenueData],
  );

  return (
    <div className="space-y-6">
      {/* ============================================================
          Row 1: Revenue Trend + Channel Donut
          ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Trend */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <RevenueLineChart data={revenueSeries} />
          </CardContent>
        </Card>

        {/* Revenue by Channel Donut */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Revenue by Channel</CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <div className="flex items-center justify-center h-[250px] text-sm text-muted-foreground">
                No channel data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Revenue by Channel">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="revenue"
                    nameKey="channel"
                    innerRadius={50}
                    outerRadius={90}
                    paddingAngle={2}
                    strokeWidth={2}
                    label={({ channel, revenue }) =>
                      `${fmtCurrency(revenue)}`
                    }
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.channel} fill={entry.fill} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              </ChartEnlargeWrapper>
            )}
            {/* Legend */}
            {pieData.length > 0 && (
              <div className="flex flex-wrap gap-3 mt-2 justify-center">
                {pieData.map((entry) => (
                  <div key={entry.channel} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm shrink-0"
                      style={{ backgroundColor: entry.fill }}
                    />
                    <span className="text-muted-foreground">{entry.channel}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ============================================================
          Row 2: Stock Alerts / Customer Health / Top Insights
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Stock Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldAlert className="size-4 text-orange-500" />
              Stock Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Critical</span>
              <Badge className="bg-red-100 text-red-700">{criticalCount}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Warning</span>
              <Badge className="bg-amber-100 text-amber-700">{warningCount}</Badge>
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              {criticalCount + warningCount === 0
                ? "All stock levels healthy"
                : `${criticalCount + warningCount} SKUs need attention`}
            </p>
          </CardContent>
        </Card>

        {/* Customer Health */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Heart className="size-4 text-pink-500" />
              Customer Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {forecastSnapshot?.forecasts?.expected_churn_next_month ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Expected Churn (30d)
                  </span>
                  <span className="text-sm font-semibold">
                    {(
                      (forecastSnapshot.forecasts.expected_churn_next_month
                        .expected_churn_rate_next_30d ?? 0) * 100
                    ).toFixed(1)}
                    %
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Model AUC
                  </span>
                  <span className="text-sm font-semibold">
                    {(
                      forecastSnapshot.forecasts.expected_churn_next_month
                        .metrics?.roc_auc ?? 0
                    ).toFixed(3)}
                  </span>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No churn data available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Top Insights Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="size-4 text-yellow-500" />
              Top Insights
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topInsights.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No insights available
              </p>
            ) : (
              <ul className="space-y-2">
                {topInsights.map((ins) => (
                  <li key={ins.insight_id} className="flex items-start gap-2">
                    <Badge
                      className={`mt-0.5 shrink-0 text-[10px] ${SEVERITY_BADGE[ins.severity] ?? SEVERITY_BADGE.low}`}
                    >
                      {ins.severity}
                    </Badge>
                    <span className="text-sm leading-snug line-clamp-2">
                      {ins.title}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ============================================================
          Row 3: Risks & Opportunities
          ============================================================ */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Risks & Opportunities</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Risks */}
            <div>
              <h4 className="flex items-center gap-2 font-semibold text-sm mb-3">
                <TrendingDown className="size-4 text-red-500" />
                Top Risks
              </h4>
              {risks.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No risks identified
                </p>
              ) : (
                <ul className="space-y-3">
                  {risks.map((risk, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-2 w-2 rounded-full bg-red-400 shrink-0" />
                      <div>
                        <p className="text-sm font-medium leading-snug">
                          {risk.title}
                        </p>
                        {risk.evidence && formatEvidence(risk.evidence) && (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatEvidence(risk.evidence)}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Opportunities */}
            <div>
              <h4 className="flex items-center gap-2 font-semibold text-sm mb-3">
                <TrendingUp className="size-4 text-green-500" />
                Top Opportunities
              </h4>
              {opportunities.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No opportunities identified
                </p>
              ) : (
                <ul className="space-y-3">
                  {opportunities.map((opp, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-2 w-2 rounded-full bg-green-400 shrink-0" />
                      <div>
                        <p className="text-sm font-medium leading-snug">
                          {opp.title}
                        </p>
                        {opp.evidence && formatEvidence(opp.evidence) && (
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatEvidence(opp.evidence)}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
