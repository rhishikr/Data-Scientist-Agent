/**
 * Client-side fallback narrative generators.
 * These produce plain-English chart annotations from existing data
 * when the backend /api/chart-narratives endpoint is unavailable.
 */
import type {
  RevenueForecastPoint,
  ForecastSnapshot,
  DemandForecastSku,
  ChurnPrediction,
  KpiCardRow,
} from "./types";

function fmtCur(n: number): string {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function revenueNarrative(
  series: RevenueForecastPoint[],
  forecast?: ForecastSnapshot | null,
): { narrative: string; action_hint: string } {
  if (!series.length) return { narrative: "", action_hint: "" };

  const actuals = series.filter((p) => p.revenue_actual != null);
  const recent = actuals.slice(-7);
  const prior = actuals.slice(-14, -7);

  let trend = "";
  if (recent.length && prior.length) {
    const recentAvg = recent.reduce((s, p) => s + (p.revenue_actual ?? 0), 0) / recent.length;
    const priorAvg = prior.reduce((s, p) => s + (p.revenue_actual ?? 0), 0) / prior.length;
    const change = priorAvg > 0 ? (recentAvg - priorAvg) / priorAvg : 0;
    const dir = change > 0.02 ? "up" : change < -0.02 ? "down" : "flat";
    trend = `Revenue is trending ${dir} (${change > 0 ? "+" : ""}${fmtPct(change)} week-over-week).`;
  }

  const rev30 = forecast?.forecasts?.forecasted_revenue?.next_30d;
  const forecastStr = rev30 ? ` 30-day forecast: ${fmtCur(rev30)}.` : "";

  return {
    narrative: `${trend}${forecastStr}`.trim(),
    action_hint: trend.includes("down")
      ? "Investigate the revenue decline and review recent campaign performance."
      : "Maintain momentum on your top-performing channels.",
  };
}

export function stockNarrative(
  skus: DemandForecastSku[],
): { narrative: string; action_hint: string } {
  if (!skus.length) return { narrative: "", action_hint: "" };

  const critical = skus.filter((s) => s.status === "critical");
  const warning = skus.filter((s) => s.status === "warning");

  if (!critical.length && !warning.length) {
    return {
      narrative: `All ${skus.length} tracked SKUs have healthy stock levels.`,
      action_hint: "No immediate restocking needed. Review levels next week.",
    };
  }

  const parts: string[] = [];
  if (critical.length) parts.push(`${critical.length} SKU${critical.length > 1 ? "s" : ""} critically low`);
  if (warning.length) parts.push(`${warning.length} need attention`);

  const topCritical = critical.slice(0, 3).map((s) => s.name || s.sku).join(", ");

  return {
    narrative: `${parts.join(" and ")} out of ${skus.length} tracked products.${topCritical ? ` Most urgent: ${topCritical}.` : ""}`,
    action_hint: critical.length
      ? `Place purchase orders for ${critical.length} critical SKU${critical.length > 1 ? "s" : ""} immediately.`
      : `Review and reorder ${warning.length} warning-level SKU${warning.length > 1 ? "s" : ""} this week.`,
  };
}

export function churnNarrative(
  customers: ChurnPrediction[],
): { narrative: string; action_hint: string } {
  if (!customers.length) return { narrative: "", action_hint: "" };

  const highRisk = customers.filter((c) => c.churn_prob_30d >= 0.7);
  const totalValue = highRisk.reduce((s, c) => s + (c.total_spend ?? 0), 0);

  if (!highRisk.length) {
    return {
      narrative: "No customers currently show high churn risk (>70%).",
      action_hint: "Continue monitoring customer engagement metrics.",
    };
  }

  return {
    narrative: `${highRisk.length} customer${highRisk.length > 1 ? "s" : ""} have >70% churn probability, representing ${fmtCur(totalValue)} in historical spend.`,
    action_hint: `Launch a retention campaign targeting these ${highRisk.length} high-risk customers to protect ${fmtCur(totalValue)} in revenue.`,
  };
}

export function overviewNarrative(
  cards: KpiCardRow[],
  skus: DemandForecastSku[],
  customers: ChurnPrediction[],
): { narrative: string; action_hint: string } {
  const parts: string[] = [];

  const revenueCard = cards.find((c) => c.id === "revenue_ytd" || c.title?.toLowerCase().includes("revenue"));
  if (revenueCard) parts.push(`Revenue: ${fmtCur(revenueCard.value)}`);

  const critical = skus.filter((s) => s.status === "critical").length;
  if (critical) parts.push(`${critical} SKU${critical > 1 ? "s" : ""} near stockout`);

  const highChurn = customers.filter((c) => c.churn_prob_30d >= 0.7).length;
  if (highChurn) parts.push(`${highChurn} customer${highChurn > 1 ? "s" : ""} at high churn risk`);

  const urgentItems = critical + (highChurn > 0 ? 1 : 0);

  return {
    narrative: parts.length ? parts.join(". ") + "." : "Dashboard data loaded.",
    action_hint: urgentItems
      ? `${urgentItems} area${urgentItems > 1 ? "s" : ""} need${urgentItems === 1 ? "s" : ""} your attention today.`
      : "No urgent actions needed right now.",
  };
}
