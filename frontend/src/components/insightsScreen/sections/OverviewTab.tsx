import React, { useEffect, useMemo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Heart,
  Lightbulb,
  MousePointerClick,
  ShieldAlert,
  ShoppingCart,
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
  ActionPlan,
  FunnelSnapshot,
} from "../dashboard/types";
import { fmtCurrency, fmtPercent, safeNum } from "../dashboard/formatters";
import { RevenueLineChart } from "../charts/RevenueLineChart";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";
import { API_BASE, apiFetch } from "../../../lib/api";

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

const SEVERITY_COLOR: Record<string, string> = {
  high: "red",
  medium: "orange",
  low: "green",
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
  actionPlan?: ActionPlan | null;
  funnelSnapshot?: FunnelSnapshot | null;
  runId?: string | null;
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
  actionPlan = null,
  funnelSnapshot = null,
  runId = null,
}: OverviewTabProps) {
  /* ---------- Fetch persisted prescription statuses ---------- */
  const [statuses, setStatuses] = useState<Record<string, string>>({});
  useEffect(() => {
    const url = runId
      ? `${API_BASE}/api/action-plan/prescriptions/statuses?run_id=${runId}`
      : `${API_BASE}/api/action-plan/prescriptions/statuses`;
    apiFetch(url)
      .then((r) => r.json())
      .then((data) => {
        const map: Record<string, string> = {};
        for (const s of data.statuses ?? []) {
          map[s.prescription_id] = s.status;
        }
        setStatuses(map);
      })
      .catch(() => {});
  }, [runId]);

  /* ---------- Stock alert counts ---------- */
  const criticalCount = useMemo(
    () => demandSkus.filter((s) => s.status === "critical").length,
    [demandSkus],
  );
  const warningCount = useMemo(
    () => demandSkus.filter((s) => s.status === "warning").length,
    [demandSkus],
  );

  /* ---------- At-risk SKUs (critical + warning) ---------- */
  const atRiskSkus = useMemo(
    () => demandSkus.filter((s) => s.status === "critical" || s.status === "warning"),
    [demandSkus],
  );
  const [stockExpanded, setStockExpanded] = useState(false);

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

  /* ---------- Row 0 summary values ---------- */
  const healthScore = safeNum(actionPlan?.health_score, 0);
  const healthColor =
    healthScore >= 70
      ? "text-green-600"
      : healthScore >= 40
        ? "text-amber-500"
        : "text-red-500";
  const healthBg =
    healthScore >= 70
      ? "bg-green-100"
      : healthScore >= 40
        ? "bg-amber-100"
        : "bg-red-100";

  const prescriptions = actionPlan?.prescriptions ?? [];
  const doneCount = prescriptions.filter(
    (p) => (statuses[p.id] ?? p.status ?? "pending") === "done",
  ).length;
  const totalPrescriptions = prescriptions.length;

  const conversionRate = safeNum(
    funnelSnapshot?.funnel_kpis?.conversion_rate,
    0,
  );
  const cartAbandonmentRate = safeNum(
    funnelSnapshot?.funnel_kpis?.cart_abandonment_rate,
    0,
  );

  return (
    <div className="space-y-6">
      {/* ============================================================
          Row 0: Health Score / Prescription Progress / Funnel / Cart
          ============================================================ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Health Score */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className={`rounded-full p-2 ${healthBg}`}>
                <Activity className={`size-5 ${healthColor}`} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Health Score</p>
                <p className="text-2xl font-bold">
                  <span className={healthColor}>{healthScore}</span>
                  <span className="text-sm font-normal text-muted-foreground">
                    /100
                  </span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Overall business health
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Prescription Progress */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-full p-2 bg-blue-100">
                <ClipboardCheck className="size-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Prescription Progress
                </p>
                <p className="text-2xl font-bold">
                  {doneCount}/{totalPrescriptions}
                  <span className="text-sm font-normal text-muted-foreground ml-1">
                    completed
                  </span>
                </p>
                <p className="text-xs text-muted-foreground">
                  Action items completed
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Funnel Conversion */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-full p-2 bg-purple-100">
                <MousePointerClick className="size-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Funnel Conversion
                </p>
                <p className="text-2xl font-bold">
                  {fmtPercent(conversionRate)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Visitor to purchase rate
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cart Abandonment */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-full p-2 bg-orange-100">
                <ShoppingCart className="size-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Cart Abandonment
                </p>
                <p className="text-2xl font-bold">
                  {fmtPercent(cartAbandonmentRate)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Carts not converted
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

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
              {/* Legend */}
              <div className="flex flex-wrap gap-3 mt-3 justify-center">
                {pieData.map((entry) => (
                  <div key={entry.channel} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="rounded-sm shrink-0"
                      style={{
                        backgroundColor: entry.fill,
                        display: "inline-block",
                        width: 12,
                        height: 12,
                        minWidth: 12,
                        minHeight: 12,
                      }}
                    />
                    <span className="text-muted-foreground capitalize">
                      {entry.channel.replace(/_/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
              </ChartEnlargeWrapper>
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
              <Badge color="red">{criticalCount}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Warning</span>
              <Badge color="orange">{warningCount}</Badge>
            </div>
            {atRiskSkus.length > 0 ? (
              <>
                <button
                  type="button"
                  onClick={() => setStockExpanded((prev) => !prev)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer pt-1"
                >
                  {stockExpanded ? (
                    <ChevronUp className="size-3.5" />
                  ) : (
                    <ChevronDown className="size-3.5" />
                  )}
                  {atRiskSkus.length} SKUs need attention
                </button>
                {stockExpanded && (
                  <div className="space-y-1.5 pt-1 max-h-[200px] overflow-y-auto">
                    {atRiskSkus.map((sku) => (
                      <div
                        key={sku.sku}
                        className="flex items-center justify-between text-xs gap-2"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span
                            className={`inline-block size-1.5 rounded-full shrink-0 ${
                              sku.status === "critical" ? "bg-red-500" : "bg-orange-400"
                            }`}
                          />
                          <span className={`truncate font-medium ${
                            sku.status === "critical" ? "text-red-600" : "text-orange-600"
                          }`}>
                            {sku.name || sku.sku}
                          </span>
                        </div>
                        <span className="text-muted-foreground shrink-0">
                          {sku.days_until_stockout != null
                            ? `${sku.days_until_stockout}d left`
                            : "No forecast"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-xs text-muted-foreground pt-1">
                All stock levels healthy
              </p>
            )}
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
                      color={SEVERITY_COLOR[ins.severity] ?? SEVERITY_COLOR.low}
                      className="mt-0.5 shrink-0 text-[10px]"
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
