import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

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
  { border: string; badgeClass: string }
> = {
  high: {
    border: "border-l-4 border-l-red-500",
    badgeClass: "bg-red-100 text-red-700",
  },
  medium: {
    border: "border-l-4 border-l-amber-500",
    badgeClass: "bg-amber-100 text-amber-700",
  },
  low: {
    border: "border-l-4 border-l-green-500",
    badgeClass: "bg-green-100 text-green-700",
  },
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
        {/* ---- Top row: severity badge + confidence ---- */}
        <div className="flex items-center justify-between">
          <Badge className={styles.badgeClass}>
            {insight.severity.charAt(0).toUpperCase() +
              insight.severity.slice(1)}
          </Badge>
          <span className="text-xs text-muted-foreground">
            Confidence: <span className="font-medium">{confidencePct}</span>
          </span>
        </div>

        {/* ---- Title ---- */}
        <h4 className="font-semibold leading-snug">{insight.title}</h4>

        {/* ---- Description ---- */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {insight.description}
        </p>

        {/* ---- Recommendation ---- */}
        {insight.recommendation && (
          <div className="rounded-md bg-muted/50 px-3 py-2">
            <p className="text-sm">
              <span className="font-medium">Recommendation: </span>
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
