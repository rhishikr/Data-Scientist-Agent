import React from "react";
import {
  DollarSign,
  ShoppingCart,
  Users,
  AlertTriangle,
  Target,
  TrendingUp,
} from "lucide-react";

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
    label: "Avg Order Value",
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
    <div className="flex rounded-md border bg-card text-card-foreground">
      {KPI_DEFS.map((def, idx) => {
        const value = getCardValue(cards, def.id);
        const Icon = def.icon;

        return (
          <div
            key={def.id}
            className="flex-1 px-4 py-3 text-center"
          >
            <div className="flex items-center justify-center gap-1.5 mb-0.5">
              <Icon className={`size-3.5 ${def.color}`} />
              <span className="text-base font-semibold tracking-tight">
                {def.format(value)}
              </span>
            </div>
            <p className="whitespace-nowrap" style={{ fontSize: 12, lineHeight: 1.2, color: "#6b7280" }}>
              {def.label}
            </p>
          </div>
        );
      })}
    </div>
  );
}
