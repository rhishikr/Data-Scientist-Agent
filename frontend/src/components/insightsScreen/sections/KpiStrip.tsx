import React from "react";
import {
  DollarSign,
  ShoppingCart,
  Users,
  AlertTriangle,
  Target,
  TrendingUp,
} from "lucide-react";

import { Card, CardContent } from "../../ui/card";
import type { KpiCardRow } from "../dashboard/types";
import { getCardValue, fmtCurrency, fmtPercent, safeNum } from "../dashboard/formatters";

/* ------------------------------------------------------------------ */
/* KPI definition map                                                  */
/* ------------------------------------------------------------------ */

type KpiDef = {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;       // Tailwind text-color class for the icon
  bgColor: string;     // Tailwind bg-color class for the icon container
  format: (v: number) => string;
};

const KPI_DEFS: KpiDef[] = [
  {
    id: "rev_ytd",
    label: "Revenue YTD",
    icon: DollarSign,
    color: "text-green-600",
    bgColor: "bg-green-50",
    format: (v) => fmtCurrency(v),
  },
  {
    id: "aov",
    label: "Average Order Value",
    icon: ShoppingCart,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    format: (v) => fmtCurrency(v),
  },
  {
    id: "active_customers_30d",
    label: "Active Customers 30d",
    icon: Users,
    color: "text-teal-600",
    bgColor: "bg-teal-50",
    format: (v) => Math.round(v).toLocaleString(),
  },
  {
    id: "churn_rate_proxy",
    label: "Churn Rate",
    icon: AlertTriangle,
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    format: (v) => fmtPercent(v),
  },
  {
    id: "conversion_rate",
    label: "Conversion Rate",
    icon: Target,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    format: (v) => fmtPercent(v),
  },
  {
    id: "roas",
    label: "ROAS",
    icon: TrendingUp,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    format: (v) => `${safeNum(v, 0).toFixed(1)}x`,
  },
];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

interface KpiStripProps {
  cards: KpiCardRow[];
}

export function KpiStrip({ cards }: KpiStripProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {KPI_DEFS.map((def) => {
        const value = getCardValue(cards, def.id);
        const Icon = def.icon;

        return (
          <Card key={def.id} className="py-3 px-4 gap-0">
            <CardContent className="p-0">
              <div className="flex items-center gap-2 mb-2">
                <div className={`rounded-md p-1.5 ${def.bgColor}`}>
                  <Icon className={`size-3.5 ${def.color}`} />
                </div>
              </div>
              <div className="text-xl font-semibold tracking-tight leading-none mb-1">
                {def.format(value)}
              </div>
              <p className="text-xs text-muted-foreground leading-tight">
                {def.label}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
