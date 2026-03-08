import React from "react";
import {
  DollarSign,
  ShoppingCart,
  Users,
  AlertTriangle,
  Target,
  TrendingUp,
  Stethoscope,
} from "lucide-react";

import type { KpiCardRow, ActionPlan } from "../dashboard/types";
import { getCardValue, fmtCurrency, fmtPercent, safeNum } from "../dashboard/formatters";

type KpiDef = {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  format: (v: number) => string;
};

const KPI_DEFS: KpiDef[] = [
  { id: "rev_ytd", label: "Revenue YTD", icon: DollarSign, color: "text-green-600", bgColor: "bg-green-50", format: (v) => fmtCurrency(v) },
  { id: "aov", label: "Avg Order Value", icon: ShoppingCart, color: "text-blue-600", bgColor: "bg-blue-50", format: (v) => fmtCurrency(v) },
  { id: "active_customers_30d", label: "Active Customers 30d", icon: Users, color: "text-teal-600", bgColor: "bg-teal-50", format: (v) => Math.round(v).toLocaleString() },
  { id: "churn_rate_proxy", label: "Churn Rate", icon: AlertTriangle, color: "text-orange-600", bgColor: "bg-orange-50", format: (v) => fmtPercent(v) },
  { id: "conversion_rate", label: "Conversion Rate", icon: Target, color: "text-purple-600", bgColor: "bg-purple-50", format: (v) => fmtPercent(v) },
  { id: "roas", label: "ROAS", icon: TrendingUp, color: "text-emerald-600", bgColor: "bg-emerald-50", format: (v) => `${safeNum(v, 0).toFixed(1)}x` },
];

function healthColor(score: number): string {
  if (score >= 80) return "text-green-600 bg-green-50 border-green-200";
  if (score >= 60) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  if (score >= 40) return "text-orange-600 bg-orange-50 border-orange-200";
  return "text-red-600 bg-red-50 border-red-200";
}

interface DiagnosisBannerProps {
  cards: KpiCardRow[];
  actionPlan?: ActionPlan | null;
}

export function DiagnosisBanner({ cards, actionPlan }: DiagnosisBannerProps) {
  const healthScore = actionPlan?.health_score ?? null;
  const healthSummary = actionPlan?.health_summary ?? null;

  return (
    <div className="space-y-2">
      {/* KPI strip */}
      <div className="flex overflow-x-auto rounded-xl border bg-card text-card-foreground">
        {KPI_DEFS.map((def) => {
          const value = getCardValue(cards, def.id);
          const Icon = def.icon;

          return (
            <div key={def.id} className="flex-1 min-w-[130px] px-4 py-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-0.5">
                <Icon className={`size-3.5 ${def.color}`} />
                <span className="text-base font-semibold tracking-tight">
                  {def.format(value)}
                </span>
              </div>
              <p
                className="whitespace-nowrap"
                style={{ fontSize: 12, lineHeight: 1.2, color: "#6b7280" }}
              >
                {def.label}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
