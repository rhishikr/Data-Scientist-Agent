import React, { useState } from "react";
import { ChevronDown, ChevronRight, ArrowRight, Zap, Clock, Target } from "lucide-react";

import { Card, CardContent } from "../../ui/card";
import { Badge } from "../../ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../../ui/collapsible";
import type { Insight } from "../dashboard/types";

/* ------------------------------------------------------------------ */
/* Severity styling map                                                */
/* ------------------------------------------------------------------ */

const SEVERITY_STYLES: Record<
  Insight["severity"],
  { border: string; color: string }
> = {
  high: { border: "border-l-4 border-l-red-500", color: "red" },
  medium: { border: "border-l-4 border-l-orange-500", color: "orange" },
  low: { border: "border-l-4 border-l-green-500", color: "green" },
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

interface InsightCardProps {
  insight: Insight;
}

export function InsightCard({ insight }: InsightCardProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const styles = SEVERITY_STYLES[insight.severity] ?? SEVERITY_STYLES.low;

  const confidencePct = Number.isFinite(insight.confidence)
    ? `${(insight.confidence * 100).toFixed(0)}%`
    : "N/A";

  return (
    <Card className={`${styles.border} gap-0`}>
      <CardContent className="p-4 space-y-3">
        {/* ---- Top row: severity badge + effort + confidence ---- */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge color={styles.color}>
            {insight.severity.charAt(0).toUpperCase() +
              insight.severity.slice(1)}
          </Badge>
          {insight.effort && (
            <Badge color={
              insight.effort === "quick-win" ? "teal" :
              insight.effort === "strategic" ? "purple" :
              "blue"
            }>
              <span className="flex items-center gap-1">
                {insight.effort === "quick-win" ? <Zap className="size-3" /> :
                 insight.effort === "strategic" ? <Target className="size-3" /> :
                 <Clock className="size-3" />}
                {insight.effort === "quick-win" ? "Quick Win" :
                 insight.effort === "strategic" ? "Strategic" : "Moderate"}
              </span>
            </Badge>
          )}
          <span className="text-xs text-muted-foreground ml-auto">
            Confidence: <span className="font-medium">{confidencePct}</span>
          </span>
        </div>

        {/* ---- Title ---- */}
        <h4 className="font-semibold leading-snug">{insight.title}</h4>

        {/* ---- Description ---- */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {insight.description}
        </p>

        {/* ---- Impact estimate ---- */}
        {insight.impact_estimate && (
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <ArrowRight className="size-3 shrink-0" />
            <span className="font-medium">{insight.impact_estimate}</span>
          </p>
        )}

        {/* ---- Recommendation (prominent) ---- */}
        {insight.recommendation && (
          <div className="rounded-md bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 px-3 py-2.5">
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100 leading-relaxed">
              {insight.recommendation}
            </p>
          </div>
        )}

        {/* ---- Tags ---- */}
        {insight.tags && insight.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {insight.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* ---- Evidence (collapsible) ---- */}
        {insight.evidence &&
          Object.keys(insight.evidence).length > 0 && (
            <Collapsible open={evidenceOpen} onOpenChange={setEvidenceOpen}>
              <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                {evidenceOpen ? (
                  <ChevronDown className="size-3.5" />
                ) : (
                  <ChevronRight className="size-3.5" />
                )}
                <span>Evidence</span>
              </CollapsibleTrigger>

              <CollapsibleContent>
                <div className="mt-2 rounded-md border bg-muted/30 p-3 text-xs overflow-x-auto">
                  <pre className="whitespace-pre-wrap break-words font-mono leading-relaxed">
                    {JSON.stringify(insight.evidence, null, 2)}
                  </pre>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
      </CardContent>
    </Card>
  );
}
