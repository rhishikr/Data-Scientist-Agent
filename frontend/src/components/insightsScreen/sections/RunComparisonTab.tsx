import React, { useMemo, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import { Badge } from "../../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../ui/select";

import {
  fmtCurrency,
  fmtPercent,
  safeNum,
} from "../dashboard/formatters";
import type {
  RunComparison,
  KpiDelta,
  ActionPlan,
  ResolvedIssue,
  CompletedPrescription,
  ComparisonAiAnalysis,
} from "../dashboard/types";
import type { PipelineRun } from "../dashboard/data";

import { Button } from "../../ui/button";
import {
  ArrowUp,
  ArrowDown,
  ArrowRight,
  Minus,
  Sparkles,
  History,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  CheckCircle2,
  AlertTriangle,
  Activity,
  Zap,
  Target,
  Play,
  Square,
  RefreshCw,
  Search,
  ChevronRight,
  GitCompareArrows,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatDeltaValue(value: number | null, format: string): string {
  if (value == null || !Number.isFinite(value)) return "—";
  switch (format) {
    case "currency":
      return fmtCurrency(value);
    case "percent":
      return fmtPercent(value);
    default:
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
}

function formatPctChange(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${(pct * 100).toFixed(1)}%`;
}

function directionIcon(direction: string) {
  switch (direction) {
    case "up":
      return <ArrowUp className="size-4 text-emerald-600" />;
    case "down":
      return <ArrowDown className="size-4 text-red-500" />;
    case "stable":
      return <Minus className="size-4 text-gray-400" />;
    default:
      return <Sparkles className="size-4 text-blue-500" />;
  }
}

function directionColor(direction: string, id: string): string {
  // For metrics where "down" is good (e.g., churn, abandonment, bounce)
  const lowerIsBetter = [
    "cart_abandonment_rate",
    "churn_rate_proxy",
    "bounce_rate",
    "payment_failure_rate",
    "payment_refund_rate",
    "stock_out_risk_pct",
    "return_rate_proxy",
  ];
  const inverted = lowerIsBetter.includes(id);

  if (direction === "up") return inverted ? "text-red-600" : "text-emerald-600";
  if (direction === "down") return inverted ? "text-emerald-600" : "text-red-600";
  return "text-gray-500";
}

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface RunComparisonTabProps {
  comparison: RunComparison | null;
  comparisonLoading: boolean;
  comparisonAi: ComparisonAiAnalysis | null;
  comparisonAiLoading: boolean;
  actionPlan: ActionPlan | null;
  runs: PipelineRun[];
  selectedRunId: string | null;
  onSelectRun: (runId: string | null) => void;
  compareWithRunId: string | null;
  onCompareWithChange: (runId: string | null) => void;
  compareEnabled: boolean;
  onCompare: () => void;
}

/* ------------------------------------------------------------------ */
/* KPI Group                                                           */
/* ------------------------------------------------------------------ */

const GROUP_ORDER = [
  "Revenue",
  "Customers",
  "Funnel",
  "Marketing",
  "Payments",
  "Product",
  "Inventory",
  "Demographics",
  "Brand",
  "Supplier",
];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function RunComparisonTab({
  comparison,
  comparisonLoading,
  comparisonAi,
  comparisonAiLoading,
  actionPlan,
  runs,
  selectedRunId,
  onSelectRun,
  compareWithRunId,
  onCompareWithChange,
  compareEnabled,
  onCompare,
}: RunComparisonTabProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(GROUP_ORDER));

  // Group deltas by KPI group
  const groupedDeltas = useMemo(() => {
    if (!comparison?.deltas) return new Map<string, KpiDelta[]>();
    const groups = new Map<string, KpiDelta[]>();
    for (const delta of comparison.deltas) {
      const group = delta.group || "Other";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group)!.push(delta);
    }
    // Sort groups by order
    const sorted = new Map<string, KpiDelta[]>();
    for (const g of GROUP_ORDER) {
      if (groups.has(g)) sorted.set(g, groups.get(g)!);
    }
    // Add any remaining groups
    for (const [g, deltas] of groups) {
      if (!sorted.has(g)) sorted.set(g, deltas);
    }
    return sorted;
  }, [comparison]);

  // Summary stats
  const summary = useMemo(() => {
    if (!comparison?.deltas) return null;
    const deltas = comparison.deltas.filter((d) => d.direction !== "new" && d.direction !== "stable");
    const improving = deltas.filter((d) => d.direction === "up").length;
    const declining = deltas.filter((d) => d.direction === "down").length;
    const stable = comparison.deltas.filter((d) => d.direction === "stable").length;
    const newMetrics = comparison.deltas.filter((d) => d.direction === "new").length;
    return { improving, declining, stable, newMetrics, total: comparison.deltas.length };
  }, [comparison]);

  // Health score from action plan
  const healthScore = actionPlan?.health_score;

  // Prescription progress
  const prescriptionStats = useMemo(() => {
    if (!actionPlan?.prescriptions) return null;
    const total = actionPlan.prescriptions.length;
    const done = actionPlan.prescriptions.filter((p) => p.status === "done").length;
    const critical = actionPlan.prescriptions.filter((p) => p.urgency === "critical").length;
    const high = actionPlan.prescriptions.filter((p) => p.urgency === "high").length;
    return { total, done, critical, high };
  }, [actionPlan]);

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  const noPrevious = comparison && !comparison.previous_snapshot;

  // Runs available for comparison (completed, excluding current)
  const comparableRuns = useMemo(() => {
    return runs
      .filter((r) => r.status === "completed" && r.id !== selectedRunId)
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  }, [runs, selectedRunId]);

  return (
    <div className="space-y-6">
      {/* Run selector + Compare button (always visible) */}
      <div className="rounded-xl bg-muted/30 px-4 py-3">
        <div className="flex items-center gap-3 flex-wrap">
          <History className="size-5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            {comparison && !noPrevious ? (
              <p className="text-sm">
                <span className="font-medium text-muted-foreground">Comparing</span>{" "}
                <span
                  className="font-semibold text-foreground"
                  style={{ textDecoration: "underline", textUnderlineOffset: "3px", textDecorationColor: "rgba(107,114,128,0.4)" }}
                >
                  {comparison.current_snapshot?.generated_at
                    ? new Date(comparison.current_snapshot.generated_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })
                    : "current run"}
                </span>
                <span className="text-muted-foreground">{" vs "}</span>
                <span
                  className="font-semibold text-foreground"
                  style={{ textDecoration: "underline", textUnderlineOffset: "3px", textDecorationColor: "rgba(107,114,128,0.4)" }}
                >
                  {comparison.previous_snapshot?.generated_at
                    ? new Date(comparison.previous_snapshot.generated_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })
                    : "previous run"}
                </span>
              </p>
            ) : comparison && noPrevious ? (
              <p className="text-sm text-muted-foreground">
                This is your first analysis run. Run the pipeline again after taking action
                on prescriptions to see how your metrics change.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Select a pipeline run to compare against, then click <strong>Compare</strong> to see how your metrics changed.
              </p>
            )}
          </div>
              {comparableRuns.length > 0 && (
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                    Compare with:
                  </span>
                  <Select
                    value={compareWithRunId ?? "__auto__"}
                    onValueChange={(v) => onCompareWithChange(v === "__auto__" ? null : v)}
                  >
                    <SelectTrigger className="w-[320px]">
                      <SelectValue placeholder="Select a run to compare" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__auto__">
                        <div className="flex items-center gap-2">
                          <span>Auto (most recent previous)</span>
                        </div>
                      </SelectItem>
                      {comparableRuns.map((r) => {
                        const date = new Date(r.started_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        });
                        return (
                          <SelectItem key={r.id} value={r.id}>
                            <div className="flex items-center gap-2">
                              <span>Run {date}</span>
                              <Badge
                                variant={r.status === "completed" ? "default" : "destructive"}
                                className="text-xs"
                              >
                                {r.status}
                              </Badge>
                              {r.duration_seconds != null && (
                                <span className="text-xs text-muted-foreground">
                                  {r.duration_seconds.toFixed(1)}s
                                </span>
                              )}
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={onCompare}
                    disabled={comparisonLoading}
                    className="bg-teal-600 hover:bg-teal-700 gap-1.5"
                    size="sm"
                  >
                    <GitCompareArrows className="size-4" />
                    {comparisonLoading ? "Comparing…" : "Compare"}
                  </Button>
                </div>
              )}
            </div>
        </div>

      {/* Loading state */}
      {comparisonLoading && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Loading comparison data...
          </CardContent>
        </Card>
      )}

      {/* ================================================================ */}
      {/* AI-POWERED INSIGHTS SECTIONS                                     */}
      {/* ================================================================ */}

      {/* AI Loading skeleton */}
      {!comparisonLoading && comparison && !noPrevious && comparisonAiLoading && (
        <Card className="border-l-4 border-l-violet-400">
          <CardContent className="p-6 space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="size-5 text-violet-500 animate-pulse" />
              <span className="text-sm font-medium text-muted-foreground animate-pulse">
                AI is analyzing your changes...
              </span>
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
              <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
              <div className="h-4 bg-muted rounded animate-pulse w-2/3" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Analysis content — only render when loaded, has data, no error */}
      {!comparisonLoading && comparison && !noPrevious && comparisonAi && !comparisonAi.error && !comparisonAiLoading && (
        <>
          {/* 1. Trend Verdict Banner */}
          {comparisonAi.trend_verdict && (
            <div
              className={`rounded-xl px-4 py-3 flex items-center gap-3 ${
                comparisonAi.trend_verdict.direction === "improving"
                  ? "bg-emerald-50 border border-emerald-200"
                  : comparisonAi.trend_verdict.direction === "declining"
                    ? "bg-red-50 border border-red-200"
                    : "bg-amber-50 border border-amber-200"
              }`}
            >
              {comparisonAi.trend_verdict.direction === "improving" ? (
                <TrendingUp className="size-5 text-emerald-600 shrink-0" />
              ) : comparisonAi.trend_verdict.direction === "declining" ? (
                <TrendingDown className="size-5 text-red-600 shrink-0" />
              ) : (
                <Activity className="size-5 text-amber-600 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`font-semibold text-sm capitalize ${
                    comparisonAi.trend_verdict.direction === "improving"
                      ? "text-emerald-700"
                      : comparisonAi.trend_verdict.direction === "declining"
                        ? "text-red-700"
                        : "text-amber-700"
                  }`}>
                    Business is {comparisonAi.trend_verdict.direction}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {comparisonAi.trend_verdict.confidence} confidence
                  </Badge>
                  {comparisonAi.cached && (
                    <Badge variant="outline" className="text-xs text-muted-foreground">cached</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{comparisonAi.trend_verdict.summary}</p>
              </div>
            </div>
          )}

          {/* 2. Executive Summary */}
          {comparisonAi.executive_summary && (
            <Card className="border-l-4 border-l-violet-400">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-5 text-violet-500" />
                  <CardTitle className="text-base">AI Change Analysis</CardTitle>
                  {comparisonAi.generated_at && (
                    <span className="text-xs text-muted-foreground ml-auto">
                      {new Date(comparisonAi.generated_at).toLocaleString("en-US", {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed">{comparisonAi.executive_summary}</p>
              </CardContent>
            </Card>
          )}

          {/* 3. Department Scorecards */}
          {comparisonAi.department_grades.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {comparisonAi.department_grades.map((dept) => {
                const gradeColors: Record<string, string> = {
                  A: "bg-emerald-100 text-emerald-700 border-emerald-300",
                  B: "bg-teal-100 text-teal-700 border-teal-300",
                  C: "bg-amber-100 text-amber-700 border-amber-300",
                  D: "bg-orange-100 text-orange-700 border-orange-300",
                  F: "bg-red-100 text-red-700 border-red-300",
                };
                const trendIcon = dept.trend === "improving"
                  ? <TrendingUp className="size-3.5 text-emerald-600" />
                  : dept.trend === "declining"
                    ? <TrendingDown className="size-3.5 text-red-500" />
                    : <Minus className="size-3.5 text-gray-400" />;
                return (
                  <Card key={dept.department} className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-muted-foreground">{dept.department}</span>
                      {trendIcon}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-bold px-2 py-0.5 rounded border ${gradeColors[dept.grade] || "bg-gray-100 text-gray-700 border-gray-300"}`}>
                        {dept.grade}
                      </span>
                      <span className="text-xs text-muted-foreground leading-tight">{dept.one_liner}</span>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {/* 4. Revenue Bridge */}
          {comparisonAi.revenue_bridge && comparisonAi.revenue_bridge.components.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Revenue Bridge</CardTitle>
                <CardDescription>
                  How the revenue change of {fmtCurrency(comparisonAi.revenue_bridge.total_change)} breaks down
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {comparisonAi.revenue_bridge.components.map((comp, i) => {
                    const maxAbs = Math.max(...comparisonAi.revenue_bridge!.components.map((c) => Math.abs(c.impact)));
                    const widthPct = maxAbs > 0 ? (Math.abs(comp.impact) / maxAbs) * 100 : 0;
                    const isPositive = comp.impact >= 0;
                    return (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-sm w-48 shrink-0 text-right">{comp.label}</span>
                        <div className="flex-1 flex items-center gap-2">
                          <div
                            className={`h-6 rounded ${isPositive ? "bg-emerald-200" : "bg-red-200"}`}
                            style={{ width: `${Math.max(widthPct, 4)}%` }}
                          />
                          <span className={`text-sm font-medium tabular-nums ${isPositive ? "text-emerald-700" : "text-red-700"}`}>
                            {isPositive ? "+" : ""}{fmtCurrency(comp.impact)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 5. Root Causes + Causal Chains */}
          {(comparisonAi.root_causes.length > 0 || comparisonAi.causal_chains.length > 0) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Root Cause Analysis</CardTitle>
                <CardDescription>Why your key metrics changed</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {comparisonAi.root_causes.map((rc, i) => (
                  <div key={i} className="rounded-lg border p-3 space-y-2">
                    <div className="flex items-center gap-2">
                      {rc.direction === "up" ? (
                        <ArrowUp className="size-4 text-emerald-600" />
                      ) : (
                        <ArrowDown className="size-4 text-red-500" />
                      )}
                      <span className="font-medium text-sm">{rc.metric}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{rc.explanation}</p>
                    {rc.contributing_factors.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {rc.contributing_factors.map((f, j) => (
                          <Badge key={j} variant="outline" className="text-xs">
                            {f}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {/* Causal chains */}
                {comparisonAi.causal_chains.map((chain, i) => (
                  <div key={`chain-${i}`} className="rounded-lg bg-muted/30 p-3 space-y-2">
                    <div className="flex items-center flex-wrap gap-1.5">
                      {chain.chain.map((step, j) => (
                        <React.Fragment key={j}>
                          <Badge variant="secondary" className="text-xs">{step}</Badge>
                          {j < chain.chain.length - 1 && (
                            <ChevronRight className="size-3.5 text-muted-foreground" />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">{chain.narrative}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* 6. Profit/Loss Drivers */}
          {(comparisonAi.profit_loss_drivers.positive.length > 0 || comparisonAi.profit_loss_drivers.negative.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="size-4 text-emerald-600" />
                    <CardTitle className="text-base text-emerald-700">Positive Drivers</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {comparisonAi.profit_loss_drivers.positive.map((d, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <CheckCircle2 className="size-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="size-4 text-red-500" />
                    <CardTitle className="text-base text-red-700">Negative Drivers</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {comparisonAi.profit_loss_drivers.negative.map((d, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <AlertTriangle className="size-4 text-red-400 shrink-0 mt-0.5" />
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 7. Prescription Report Card */}
          {comparisonAi.prescription_report_card.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle className="size-5 text-violet-600" />
                  <CardTitle className="text-base">Prescription Report Card</CardTitle>
                </div>
                <CardDescription>Did the actions you took actually work?</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {comparisonAi.prescription_report_card.map((rx, i) => {
                  const verdictStyle: Record<string, string> = {
                    effective: "bg-emerald-100 text-emerald-700 border-emerald-300",
                    partially_effective: "bg-amber-100 text-amber-700 border-amber-300",
                    no_impact: "bg-gray-100 text-gray-700 border-gray-300",
                    too_early: "bg-blue-100 text-blue-700 border-blue-300",
                  };
                  return (
                    <div key={i} className="rounded-lg border p-3 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm">{rx.prescription_title}</span>
                        <Badge variant="outline" className={`text-xs ${verdictStyle[rx.verdict] || ""}`}>
                          {rx.verdict.replace(/_/g, " ")}
                        </Badge>
                        {rx.related_kpi_impact && (
                          <span className="text-xs font-medium text-emerald-600">{rx.related_kpi_impact}</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{rx.evidence}</p>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          {/* 8. Missed Opportunities */}
          {comparisonAi.missed_opportunities.length > 0 && (
            <Card className="border-l-4 border-l-amber-400">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-5 text-amber-500" />
                  <CardTitle className="text-base">Missed Opportunities</CardTitle>
                </div>
                <CardDescription>Prescriptions not acted on and their estimated cost</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {comparisonAi.missed_opportunities.map((mo, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg border p-3">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm">{mo.prescription_title}</span>
                        <Badge variant="outline" className={`text-xs ${
                          mo.urgency_now === "critical" ? "border-red-200 bg-red-50 text-red-700"
                            : mo.urgency_now === "high" ? "border-orange-200 bg-orange-50 text-orange-700"
                              : "border-gray-200 bg-gray-50 text-gray-700"
                        }`}>
                          {mo.urgency_now}
                        </Badge>
                        <Badge variant="outline" className="text-xs">{mo.status}</Badge>
                      </div>
                      <p className="text-sm text-red-600 font-medium">{mo.estimated_cost_of_inaction}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* 9. Quick Wins + Next 30-Day Targets */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Quick Wins */}
            {comparisonAi.quick_wins.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <Zap className="size-5 text-amber-500" />
                    <CardTitle className="text-base">Quick Wins</CardTitle>
                  </div>
                  <CardDescription>Low-effort actions you can take right now</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {comparisonAi.quick_wins.map((qw, i) => (
                    <div key={i} className="rounded-lg border p-3 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm">{qw.action}</span>
                        <Badge variant="outline" className="text-xs">{qw.effort}</Badge>
                      </div>
                      <p className="text-xs text-emerald-600 font-medium">{qw.expected_impact}</p>
                      <p className="text-xs text-muted-foreground">{qw.data_point}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Next 30-Day Targets */}
            {comparisonAi.next_30_day_targets.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <Target className="size-5 text-blue-500" />
                    <CardTitle className="text-base">Next 30-Day Targets</CardTitle>
                  </div>
                  <CardDescription>Measurable goals to hit this month</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {comparisonAi.next_30_day_targets.map((t, i) => (
                    <div key={i} className="rounded-lg border p-3 space-y-1.5">
                      <span className="font-medium text-sm">{t.target}</span>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-muted-foreground">{t.current_value}</span>
                        <ArrowRight className="size-3 text-muted-foreground" />
                        <span className="font-medium text-blue-600">{t.target_value}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{t.how}</p>
                      <p className="text-xs text-emerald-600 font-medium">{t.expected_impact}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          {/* 10. Start / Stop / Keep Doing */}
          {(comparisonAi.start_doing.length > 0 || comparisonAi.stop_doing.length > 0 || comparisonAi.keep_doing.length > 0) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Strategic Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {comparisonAi.start_doing.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-emerald-700 font-medium text-sm">
                        <Play className="size-4" />
                        <span>Start Doing</span>
                      </div>
                      <ul className="space-y-1.5">
                        {comparisonAi.start_doing.map((s, i) => (
                          <li key={i} className="text-sm text-muted-foreground pl-5 relative before:content-[''] before:absolute before:left-1 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-emerald-400">
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {comparisonAi.stop_doing.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-red-700 font-medium text-sm">
                        <Square className="size-4" />
                        <span>Stop Doing</span>
                      </div>
                      <ul className="space-y-1.5">
                        {comparisonAi.stop_doing.map((s, i) => (
                          <li key={i} className="text-sm text-muted-foreground pl-5 relative before:content-[''] before:absolute before:left-1 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-red-400">
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {comparisonAi.keep_doing.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-blue-700 font-medium text-sm">
                        <RefreshCw className="size-4" />
                        <span>Keep Doing</span>
                      </div>
                      <ul className="space-y-1.5">
                        {comparisonAi.keep_doing.map((s, i) => (
                          <li key={i} className="text-sm text-muted-foreground pl-5 relative before:content-[''] before:absolute before:left-1 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-blue-400">
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 11. Anomalies */}
          {comparisonAi.anomalies.length > 0 && (
            <Card className="border-l-4 border-l-red-400">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Search className="size-5 text-red-500" />
                  <CardTitle className="text-base">Anomalies Detected</CardTitle>
                </div>
                <CardDescription>Unexpected changes that need investigation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {comparisonAi.anomalies.map((a, i) => (
                  <div key={i} className="rounded-lg border border-red-100 bg-red-50/30 p-3 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{a.metric}</span>
                      <Badge variant="outline" className="text-xs text-red-600 border-red-200">{a.change}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{a.why_unexpected}</p>
                    <p className="text-xs text-blue-600">Investigate: {a.suggested_investigation}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* KPI Delta Table grouped */}
      {!comparisonLoading && comparison && !noPrevious && (
        <div className="space-y-4">
          {Array.from(groupedDeltas.entries()).map(([group, deltas]) => (
            <Card key={group}>
              <CardHeader
                className="cursor-pointer select-none"
                onClick={() => toggleGroup(group)}
              >
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{group}</CardTitle>
                  <div className="flex items-center gap-2">
                    {(() => {
                      const up = deltas.filter((d) => d.direction === "up").length;
                      const down = deltas.filter((d) => d.direction === "down").length;
                      return (
                        <>
                          {up > 0 && (
                            <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50">
                              {up} up
                            </Badge>
                          )}
                          {down > 0 && (
                            <Badge variant="outline" className="text-red-600 border-red-200 bg-red-50">
                              {down} down
                            </Badge>
                          )}
                        </>
                      );
                    })()}
                    <span className="text-xs text-muted-foreground">
                      {expandedGroups.has(group) ? "collapse" : "expand"}
                    </span>
                  </div>
                </div>
              </CardHeader>
              {expandedGroups.has(group) && (
                <CardContent className="pt-0">
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-muted/50 text-muted-foreground">
                          <th className="text-left p-3 font-medium">Metric</th>
                          <th className="text-right p-3 font-medium">Current</th>
                          <th className="text-right p-3 font-medium">Previous</th>
                          <th className="text-right p-3 font-medium">Change</th>
                          <th className="text-center p-3 font-medium w-16">Trend</th>
                        </tr>
                      </thead>
                      <tbody>
                        {deltas.map((delta) => (
                          <tr key={delta.id} className="border-t hover:bg-muted/20">
                            <td className="p-3 font-medium">{delta.title}</td>
                            <td className="p-3 text-right tabular-nums">
                              {formatDeltaValue(delta.current_value, delta.format)}
                            </td>
                            <td className="p-3 text-right tabular-nums text-muted-foreground">
                              {delta.previous_value != null
                                ? formatDeltaValue(delta.previous_value, delta.format)
                                : "—"}
                            </td>
                            <td className={`p-3 text-right tabular-nums font-medium ${directionColor(delta.direction, delta.id)}`}>
                              {formatPctChange(delta.percent_change)}
                            </td>
                            <td className="p-3 text-center">
                              {directionIcon(delta.direction)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Resolved Issues & New Risks */}
      {!comparisonLoading &&
        comparison &&
        !noPrevious &&
        ((comparison.resolved_issues && comparison.resolved_issues.length > 0) ||
          (comparison.new_risks && comparison.new_risks.length > 0)) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Resolved Issues */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-5 text-emerald-600" />
                  <CardTitle className="text-base">Resolved Issues</CardTitle>
                </div>
                <CardDescription>
                  Issues from the previous run that are no longer flagged
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {comparison.resolved_issues && comparison.resolved_issues.length > 0 ? (
                  comparison.resolved_issues.map((issue, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded-md border p-2"
                    >
                      <Badge
                        variant="outline"
                        className={
                          issue.severity === "critical"
                            ? "border-red-200 bg-red-50 text-red-700"
                            : issue.severity === "high"
                              ? "border-orange-200 bg-orange-50 text-orange-700"
                              : issue.severity === "medium"
                                ? "border-amber-200 bg-amber-50 text-amber-700"
                                : "border-gray-200 bg-gray-50 text-gray-700"
                        }
                      >
                        {issue.severity}
                      </Badge>
                      <span className="text-sm">{issue.title}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No resolved issues</p>
                )}
              </CardContent>
            </Card>

            {/* New Risks */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-5 text-red-500" />
                  <CardTitle className="text-base">New Risks</CardTitle>
                </div>
                <CardDescription>
                  Newly detected risks since the previous run
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {comparison.new_risks && comparison.new_risks.length > 0 ? (
                  comparison.new_risks.map((risk, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded-md border p-2"
                    >
                      <Badge
                        variant="outline"
                        className={
                          risk.severity === "critical"
                            ? "border-red-200 bg-red-50 text-red-700"
                            : risk.severity === "high"
                              ? "border-orange-200 bg-orange-50 text-orange-700"
                              : risk.severity === "medium"
                                ? "border-amber-200 bg-amber-50 text-amber-700"
                                : "border-gray-200 bg-gray-50 text-gray-700"
                        }
                      >
                        {risk.severity}
                      </Badge>
                      <span className="text-sm">{risk.title}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No new risks detected</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

      {/* Completed Prescriptions Impact */}
      {!comparisonLoading &&
        comparison &&
        !noPrevious &&
        comparison.completed_prescriptions &&
        comparison.completed_prescriptions.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CheckCircle className="size-5 text-violet-600" />
                <CardTitle className="text-base">Prescription Impact</CardTitle>
              </div>
              <CardDescription>
                Completed prescriptions from the previous run and their effect on KPIs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {comparison.completed_prescriptions.map((rx) => (
                <div key={rx.id} className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{rx.title}</span>
                    <Badge variant="outline" className="text-xs">
                      {rx.category}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={
                        rx.urgency === "critical"
                          ? "border-red-200 bg-red-50 text-red-700 text-xs"
                          : rx.urgency === "high"
                            ? "border-orange-200 bg-orange-50 text-orange-700 text-xs"
                            : "border-gray-200 bg-gray-50 text-gray-700 text-xs"
                      }
                    >
                      {rx.urgency}
                    </Badge>
                  </div>
                  {rx.related_kpi_changes.length > 0 && (
                    <div className="space-y-1 pl-2">
                      {rx.related_kpi_changes.map((kpi) => (
                        <div
                          key={kpi.id}
                          className="flex items-center gap-2 text-sm"
                        >
                          {kpi.direction === "up" ? (
                            <ArrowUp className="size-3.5 text-emerald-600" />
                          ) : kpi.direction === "down" ? (
                            <ArrowDown className="size-3.5 text-red-500" />
                          ) : (
                            <Minus className="size-3.5 text-gray-400" />
                          )}
                          <span className="text-muted-foreground">
                            {kpi.title}
                          </span>
                          {kpi.percent_change != null && (
                            <span
                              className={`tabular-nums font-medium ${
                                kpi.direction === "up"
                                  ? "text-emerald-600"
                                  : kpi.direction === "down"
                                    ? "text-red-600"
                                    : "text-gray-500"
                              }`}
                            >
                              {formatPctChange(kpi.percent_change)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

      {/* No previous run — show tips */}
      {!comparisonLoading && noPrevious && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-amber-500" />
              <CardTitle>How Follow-Up Works</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              "Review your Action Plan tab and act on the prescriptions",
              "Mark prescriptions as 'done' with notes about what you changed",
              "Run the pipeline again after making changes (days or weeks later)",
              "Return to this tab to see which KPIs improved and which need more attention",
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="rounded-full bg-teal-100 text-teal-700 text-xs font-bold w-6 h-6 flex items-center justify-center shrink-0 mt-0.5">
                  {i + 1}
                </div>
                <span className="text-sm">{step}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Run History */}
      {runs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Run History</CardTitle>
            <CardDescription>
              Past pipeline runs — click to view that run's data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50 text-muted-foreground">
                    <th className="text-left p-3 font-medium">Run</th>
                    <th className="text-left p-3 font-medium">Started</th>
                    <th className="text-left p-3 font-medium">Status</th>
                    <th className="text-right p-3 font-medium">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 10).map((run) => (
                    <tr
                      key={run.id}
                      className={`border-t cursor-pointer hover:bg-muted/20 ${
                        selectedRunId === run.id ? "bg-teal-50" : ""
                      }`}
                      onClick={() =>
                        onSelectRun(selectedRunId === run.id ? null : run.id)
                      }
                    >
                      <td className="p-3 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                      <td className="p-3">
                        {run.started_at
                          ? new Date(run.started_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={run.status === "completed" ? "default" : "secondary"}
                          className={
                            run.status === "completed"
                              ? "bg-emerald-100 text-emerald-700"
                              : run.status === "failed"
                                ? "bg-red-100 text-red-700"
                                : ""
                          }
                        >
                          {run.status}
                        </Badge>
                      </td>
                      <td className="p-3 text-right tabular-nums">
                        {run.duration_seconds != null
                          ? `${run.duration_seconds.toFixed(0)}s`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
