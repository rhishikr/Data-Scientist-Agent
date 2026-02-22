import React from "react";
import {
  Sparkles,
  CheckCircle2,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Skeleton } from "../../ui/skeleton";
import type { AiAnalysis } from "../dashboard/types";

/* ------------------------------------------------------------------ */
/* Loading skeleton                                                    */
/* ------------------------------------------------------------------ */

function AiAnalysisSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-5 w-48" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Timestamp formatter                                                 */
/* ------------------------------------------------------------------ */

function formatTimestamp(iso: string | undefined): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

interface AiAnalysisPanelProps {
  data: AiAnalysis | null;
  loading: boolean;
}

export function AiAnalysisPanel({ data, loading }: AiAnalysisPanelProps) {
  /* -- Loading state -- */
  if (loading) {
    return <AiAnalysisSkeleton />;
  }

  /* -- Error / empty state -- */
  if (!data || data.error) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">
            {data?.error ?? "Analysis unavailable"}
          </p>
        </CardContent>
      </Card>
    );
  }

  const timestamp = formatTimestamp(data.generated_at);

  return (
    <Card className="border-l-4" style={{ borderImageSource: "linear-gradient(to bottom, #14b8a6, #3b82f6)", borderImageSlice: 1 }}>
      {/* ---- Header ---- */}
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-teal-500" />
            <CardTitle className="text-base">AI-Powered Analysis</CardTitle>
          </div>

          <div className="flex items-center gap-2">
            {data.cached && (
              <Badge variant="secondary" className="text-xs">
                Cached
              </Badge>
            )}
            {timestamp && (
              <span className="text-xs text-muted-foreground">{timestamp}</span>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* ---- Main analysis paragraph ---- */}
        {data.analysis && (
          <p className="text-sm leading-relaxed">{data.analysis}</p>
        )}

        {/* ---- Key Findings ---- */}
        {data.key_findings && data.key_findings.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Key Findings</h4>
            <ol className="space-y-1.5">
              {data.key_findings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="size-4 mt-0.5 shrink-0 text-teal-500" />
                  <span className="leading-relaxed">{finding}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* ---- Recommendations ---- */}
        {data.recommendations && data.recommendations.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Recommendations</h4>
            <ul className="space-y-1.5">
              {data.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <ArrowRight className="size-4 mt-0.5 shrink-0 text-blue-500" />
                  <span className="leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ---- Risks ---- */}
        {data.risks && data.risks.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Risks</h4>
            <ul className="space-y-1.5">
              {data.risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <AlertTriangle className="size-4 mt-0.5 shrink-0 text-amber-500" />
                  <span className="leading-relaxed">{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
