import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Package,
  Users,
  DollarSign,
  Megaphone,
  ShoppingBag,
  Zap,
  Clock,
  Target,
  Check,
  X,
  RotateCcw,
} from "lucide-react";

import { Card, CardContent } from "../../ui/card";
import { Badge } from "../../ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../../ui/collapsible";
import type { Prescription, PrescriptionStatus } from "../dashboard/types";

const URGENCY_STYLES: Record<string, { border: string; color: string }> = {
  critical: { border: "border-l-4 border-l-red-500", color: "red" },
  high: { border: "border-l-4 border-l-orange-500", color: "orange" },
  medium: { border: "border-l-4 border-l-blue-500", color: "blue" },
  low: { border: "border-l-4 border-l-green-500", color: "green" },
};

const EFFORT_STYLES: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  "quick-win": { icon: <Zap className="size-3" />, label: "Quick Win", color: "teal" },
  moderate: { icon: <Clock className="size-3" />, label: "Moderate", color: "blue" },
  strategic: { icon: <Target className="size-3" />, label: "Strategic", color: "purple" },
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  inventory: <Package className="size-4" />,
  customer: <Users className="size-4" />,
  revenue: <DollarSign className="size-4" />,
  marketing: <Megaphone className="size-4" />,
  product: <ShoppingBag className="size-4" />,
};

interface PrescriptionCardProps {
  prescription: Prescription;
  onStatusChange?: (id: string, status: PrescriptionStatus) => void;
}

export function PrescriptionCard({ prescription, onStatusChange }: PrescriptionCardProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const urgStyle = URGENCY_STYLES[prescription.urgency] ?? URGENCY_STYLES.medium;
  const effortStyle = EFFORT_STYLES[prescription.effort] ?? EFFORT_STYLES.moderate;

  const status = prescription.status ?? "pending";
  const isDone = status === "done";
  const isDismissed = status === "dismissed";
  const isResolved = isDone || isDismissed;

  return (
    <Card className={`${urgStyle.border} gap-0 transition-opacity ${isResolved ? "opacity-60" : ""}`}>
      <CardContent className="p-4 space-y-3">
        {/* Top row: urgency + effort + impact + action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge color={urgStyle.color}>
            {prescription.urgency.charAt(0).toUpperCase() + prescription.urgency.slice(1)}
          </Badge>
          <Badge color={effortStyle.color}>
            <span className="flex items-center gap-1">
              {effortStyle.icon}
              {effortStyle.label}
            </span>
          </Badge>
          {isDone && (
            <Badge color="green">
              <span className="flex items-center gap-1">
                <Check className="size-3" />
                Done
              </span>
            </Badge>
          )}
          {isDismissed && (
            <Badge color="gray">
              <span className="flex items-center gap-1">
                <X className="size-3" />
                Dismissed
              </span>
            </Badge>
          )}
          {prescription.impact_estimate && (
            <span className="text-xs text-muted-foreground ml-auto">
              {prescription.impact_estimate}
            </span>
          )}
        </div>

        {/* Title with category icon */}
        <div className="flex items-start gap-2">
          <span className="text-muted-foreground mt-0.5">
            {CATEGORY_ICONS[prescription.category] ?? <ShoppingBag className="size-4" />}
          </span>
          <h4 className={`font-semibold leading-snug ${isDone ? "line-through text-muted-foreground" : ""}`}>
            {prescription.title}
          </h4>
        </div>

        {/* Description */}
        <p className={`text-sm leading-relaxed ${isDone ? "line-through text-muted-foreground" : "text-muted-foreground"}`}>
          {prescription.description}
        </p>

        {/* Action buttons + Evidence row */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Action buttons */}
          {onStatusChange && (
            <div className="flex items-center gap-1.5">
              {!isDone && (
                <button
                  onClick={() => onStatusChange(prescription.id, "done")}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 transition-colors cursor-pointer"
                >
                  <Check className="size-3" />
                  {isDismissed ? "Mark Done" : "Done"}
                </button>
              )}
              {!isDismissed && !isDone && (
                <button
                  onClick={() => onStatusChange(prescription.id, "dismissed")}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors cursor-pointer"
                >
                  <X className="size-3" />
                  Dismiss
                </button>
              )}
              {isResolved && (
                <button
                  onClick={() => onStatusChange(prescription.id, "pending")}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
                >
                  <RotateCcw className="size-3" />
                  Reopen
                </button>
              )}
            </div>
          )}

          {/* Evidence (collapsible) - pushed to right */}
          {prescription.evidence && Object.keys(prescription.evidence).length > 0 && (
            <div className="ml-auto">
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
                      {JSON.stringify(prescription.evidence, null, 2)}
                    </pre>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
