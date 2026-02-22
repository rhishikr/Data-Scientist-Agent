import React, { useMemo, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Input } from "../../ui/input";

import type {
  Insight,
  ForecastSnapshot,
  AiAnalysis,
} from "../dashboard/types";
import { InsightCard } from "../charts/InsightCard";
import { AiAnalysisPanel } from "../charts/AiAnalysisPanel";

import {
  Search,
  TrendingUp,
  Lightbulb,
  CheckCircle,
  Brain,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface AiInsightsTabProps {
  insights: Insight[];
  forecastSnapshot: ForecastSnapshot | null;
  aiAnalysis: AiAnalysis | null;
  aiAnalysisLoading: boolean;
}

// ---------------------------------------------------------------------------
// Severity type
// ---------------------------------------------------------------------------
type SeverityFilter = "all" | "high" | "medium" | "low";

const severityOptions: { value: SeverityFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const severityColorMap: Record<SeverityFilter, { bg: string; text: string }> = {
  all: { bg: "var(--primary)", text: "var(--primary-foreground)" },
  high: { bg: "#dc2626", text: "#ffffff" },
  medium: { bg: "#f59e0b", text: "#ffffff" },
  low: { bg: "#2563eb", text: "#ffffff" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function AiInsightsTab({
  insights,
  forecastSnapshot,
  aiAnalysis,
  aiAnalysisLoading,
}: AiInsightsTabProps) {
  const [selectedSeverity, setSelectedSeverity] =
    useState<SeverityFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Executive insights
  const keyDrivers =
    forecastSnapshot?.executive_insights?.key_drivers_of_growth_decline ?? [];
  const recommendedActions =
    forecastSnapshot?.executive_insights?.recommended_actions_rule_based ?? [];

  // Filtered insights
  const filteredInsights = useMemo(() => {
    if (!insights || insights.length === 0) return [];

    return insights.filter((insight) => {
      // Severity filter
      if (selectedSeverity !== "all" && insight.severity !== selectedSeverity) {
        return false;
      }

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = insight.title?.toLowerCase().includes(q);
        const matchesDesc = insight.description?.toLowerCase().includes(q);
        const matchesRec = insight.recommendation?.toLowerCase().includes(q);
        const matchesTags = insight.tags?.some((t) =>
          t.toLowerCase().includes(q),
        );
        if (!matchesTitle && !matchesDesc && !matchesRec && !matchesTags) {
          return false;
        }
      }

      return true;
    });
  }, [insights, selectedSeverity, searchQuery]);

  // Counts per severity
  const severityCounts = useMemo(() => {
    if (!insights) return { all: 0, high: 0, medium: 0, low: 0 };
    return {
      all: insights.length,
      high: insights.filter((i) => i.severity === "high").length,
      medium: insights.filter((i) => i.severity === "medium").length,
      low: insights.filter((i) => i.severity === "low").length,
    };
  }, [insights]);

  const hasInsights = insights && insights.length > 0;

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Row 1: AI Analysis Panel                                            */}
      {/* ------------------------------------------------------------------ */}
      <AiAnalysisPanel data={aiAnalysis} loading={aiAnalysisLoading} />

      {/* ------------------------------------------------------------------ */}
      {/* Row 2: Filter Bar                                                   */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {/* Severity filter buttons */}
        <div className="flex items-center gap-1.5">
          {severityOptions.map((opt) => {
            const isActive = selectedSeverity === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setSelectedSeverity(opt.value)}
                className={`
                  inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5
                  text-xs font-medium transition-colors
                  ${
                    isActive
                      ? "border-transparent"
                      : "border-input bg-background text-foreground hover:bg-accent hover:text-accent-foreground"
                  }
                `}
                style={
                  isActive
                    ? { backgroundColor: severityColorMap[opt.value].bg, color: severityColorMap[opt.value].text }
                    : undefined
                }
              >
                {opt.label}
                <span
                  className={`
                    ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] leading-none
                    ${isActive ? "bg-white/20" : "bg-muted"}
                  `}
                >
                  {severityCounts[opt.value]}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search input */}
        <div className="relative flex-1 w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search insights..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 3: Insight Cards Grid                                           */}
      {/* ------------------------------------------------------------------ */}
      {!hasInsights ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Brain className="size-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <h3 className="font-semibold mb-2">No insights available</h3>
            <p className="text-sm text-muted-foreground">
              Insights will appear here once the analysis pipeline has generated
              them.
            </p>
          </CardContent>
        </Card>
      ) : filteredInsights.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="size-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <h3 className="font-semibold mb-2">No matching insights</h3>
            <p className="text-sm text-muted-foreground">
              Try adjusting your filters or search query.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredInsights.map((insight) => (
            <InsightCard key={insight.insight_id} insight={insight} />
          ))}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Row 4: Executive Section - Key Drivers & Recommended Actions        */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Key Drivers */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingUp className="size-5 text-teal-600" />
              <CardTitle>Key Drivers</CardTitle>
            </div>
            <CardDescription>
              Key drivers of growth and decline
            </CardDescription>
          </CardHeader>
          <CardContent>
            {keyDrivers.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No key drivers data available
              </p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {keyDrivers.map((driver, idx) => {
                  // Parse driver string for display
                  const [left, ...rest] = driver.split(":");
                  const right = rest.join(":").trim();
                  const dataset = left.replace(/_/g, " ");

                  const effectMatch = right.match(/effect=([0-9.]+)/);
                  const effect = effectMatch ? Number(effectMatch[1]) : null;

                  const methodMatch = right.match(/\(([^)]+)\)/);
                  const method = methodMatch?.[1] ?? null;

                  const statement = right
                    .replace(/\([^)]*\)/g, "")
                    .replace(/\s*p_adj=.*$/, "")
                    .trim();

                  return (
                    <div
                      key={idx}
                      className="rounded-md border p-3 text-sm leading-relaxed"
                    >
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">
                          {dataset}
                        </Badge>
                        {method && (
                          <Badge variant="secondary" className="text-xs">
                            {method}
                          </Badge>
                        )}
                        {effect !== null && (
                          <span className="text-xs text-muted-foreground">
                            effect {effect.toFixed(2)}
                          </span>
                        )}
                      </div>
                      <p className="text-muted-foreground break-words whitespace-normal">
                        {statement}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recommended Actions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Lightbulb className="size-5 text-amber-500" />
              <CardTitle>Recommended Actions</CardTitle>
            </div>
            <CardDescription>
              Rule-based recommended actions from executive insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recommendedActions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No recommendations available
              </p>
            ) : (
              <ul className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {recommendedActions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <CheckCircle className="size-4 mt-0.5 shrink-0 text-teal-600" />
                    <span className="text-sm leading-relaxed">{action}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
