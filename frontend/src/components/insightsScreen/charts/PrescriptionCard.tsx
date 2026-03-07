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
} from "lucide-react";

import { Card, CardContent } from "../../ui/card";
import { Badge } from "../../ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../../ui/collapsible";
import type { Prescription } from "../dashboard/types";

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
}

export function PrescriptionCard({ prescription }: PrescriptionCardProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const urgStyle = URGENCY_STYLES[prescription.urgency] ?? URGENCY_STYLES.medium;
  const effortStyle = EFFORT_STYLES[prescription.effort] ?? EFFORT_STYLES.moderate;

  return (
    <Card className={`${urgStyle.border} gap-0`}>
      <CardContent className="p-4 space-y-3">
        {/* Top row: urgency + effort + impact */}
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
          <h4 className="font-semibold leading-snug">{prescription.title}</h4>
        </div>

        {/* Description */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {prescription.description}
        </p>

        {/* Evidence (collapsible) */}
        {prescription.evidence && Object.keys(prescription.evidence).length > 0 && (
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
        )}
      </CardContent>
    </Card>
  );
}
