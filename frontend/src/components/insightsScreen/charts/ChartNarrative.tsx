import React from "react";
import { Lightbulb, ArrowRight } from "lucide-react";

interface ChartNarrativeProps {
  narrative: string;
  actionHint?: string;
}

export function ChartNarrative({ narrative, actionHint }: ChartNarrativeProps) {
  if (!narrative) return null;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/30 px-4 py-3 mb-3">
      <div className="flex items-start gap-2.5">
        <Lightbulb className="size-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
        <div className="space-y-1 min-w-0">
          <p className="text-sm text-foreground leading-relaxed">{narrative}</p>
          {actionHint && (
            <p className="text-sm font-medium text-blue-700 dark:text-blue-300 flex items-center gap-1.5">
              <ArrowRight className="size-3.5 shrink-0" />
              {actionHint}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
