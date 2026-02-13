// dashboard/widgetRegistry.tsx
import React from "react";
import {
  Users,
  TrendingUp,
  AlertTriangle,
  BarChart3,
  ShoppingCart,
  DollarSign,
  Target,
  Percent,
  UserCheck,
  UserPlus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import { Badge } from "../../ui/badge";

import type { WidgetDefinition, ForecastSnapshot } from "./types";
import { fmtCurrency, fmtCurrency2, fmtPercent } from "./formatters";

export function buildWidgetRegistry({
  KPI,
  channelRevenueData,
  topCustomers,
  forecastSnapshot,
}: {
  KPI: any;
  channelRevenueData: Array<{ channel: string; revenue: number }>;
  topCustomers: Array<{
    id: string;
    name: string;
    segment: string;
    recency: string;
    frequency: number;
    monetary: string;
    churn: number;
  }>;
  forecastSnapshot: ForecastSnapshot | null;
}): Record<string, WidgetDefinition> {
  return {
    // ------------------------
    // Customer KPIs
    // ------------------------
    "active-customers": {
      id: "active-customers",
      title: "Active Customers (30d)",
      description: "Customers with activity/purchases in the last 30 days",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: Users,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Active Customers (30d)</CardTitle>
            <Users className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {KPI.activeCustomers30d.toLocaleString()}
            </div>
            {/* <p className="text-xs text-muted-foreground">As of {KPI.asOf}</p> */}
          </CardContent>
        </Card>
      ),
    },

    "new-customers": {
      id: "new-customers",
      title: "New Customers (30d)",
      description: "Newly acquired customers in last 30 days",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: UserPlus,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">New Customers (30d)</CardTitle>
            <UserPlus className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {KPI.newCustomers30d.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              New vs Returning is heavily skewed to returning in this dataset
            </p>
          </CardContent>
        </Card>
      ),
    },

    "returning-customers": {
      id: "returning-customers",
      title: "Returning Customers",
      description: "Returning customers (per your KPI definition)",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: RefreshCw,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Returning Customers</CardTitle>
            <RefreshCw className="size-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {KPI.returningCustomers30d.toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Repeat Purchase Rate:{" "}
              <span className="font-medium">
                {fmtPercent(KPI.repeatPurchaseRate)}
              </span>
            </p>
          </CardContent>
        </Card>
      ),
    },

    "churn-risk": {
      id: "churn-risk",
      title: "Churn Rate (proxy)",
      description: "Proxy churn rate based on your heuristic",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: AlertTriangle,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Churn Rate (proxy)</CardTitle>
            <AlertTriangle className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtPercent(KPI.churnRateProxy)}</div>
            <p className="text-xs text-muted-foreground">
              (Proxy) Retention: {fmtPercent(KPI.retentionRateProxy)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    "retention-rate": {
      id: "retention-rate",
      title: "Retention Rate (proxy)",
      description: "Proxy retention rate based on your heuristic",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: UserCheck,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Retention Rate (proxy)</CardTitle>
            <UserCheck className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtPercent(KPI.retentionRateProxy)}</div>
            <p className="text-xs text-muted-foreground">
              This is not cohort-based retention (yet)
            </p>
          </CardContent>
        </Card>
      ),
    },

    "avg-customer-value": {
      id: "avg-customer-value",
      title: "Average CLV",
      description: "Average customer lifetime value",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: DollarSign,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Average CLV</CardTitle>
            <DollarSign className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtCurrency2(KPI.avgClv)}</div>
            {/* <p className="text-xs text-muted-foreground">As of {KPI.asOf}</p> */}
          </CardContent>
        </Card>
      ),
    },

    "top-customers": {
      id: "top-customers",
      title: "Top Customers",
      description: "From customers.json (computed view)",
      type: "table",
      defaultSize: "large",
      category: "Customer",
      icon: Users,
      render: () => (
        <Card>
          <CardHeader>
            <CardTitle>Top Customers</CardTitle>
            <CardDescription>Spend + orders + recency</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left pb-3 text-sm">Customer</th>
                    <th className="text-left pb-3 text-sm">Segment</th>
                    <th className="text-left pb-3 text-sm">Recency</th>
                    <th className="text-right pb-3 text-sm">Orders</th>
                    <th className="text-right pb-3 text-sm">Spend</th>
                    <th className="text-right pb-3 text-sm">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {topCustomers.map((customer) => (
                    <tr
                      key={customer.id}
                      className="border-b hover:bg-slate-50"
                    >
                      <td className="py-3">
                        <div>
                          <p className="text-sm">{customer.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {customer.id}
                          </p>
                        </div>
                      </td>
                      <td className="py-3">
                        <Badge
                          variant="outline"
                          className={
                            customer.segment === "Top Buyer"
                              ? "text-green-600 border-green-200"
                              : customer.segment === "At-Risk"
                                ? "text-orange-600 border-orange-200"
                                : "text-blue-600 border-blue-200"
                          }
                        >
                          {customer.segment}
                        </Badge>
                      </td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {customer.recency}
                      </td>
                      <td className="py-3 text-sm text-right">
                        {customer.frequency}
                      </td>
                      <td className="py-3 text-sm text-right">
                        {customer.monetary}
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                customer.churn > 0.7
                                  ? "bg-red-500"
                                  : customer.churn > 0.3
                                    ? "bg-orange-500"
                                    : "bg-green-500"
                              }`}
                              style={{ width: `${customer.churn * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-10">
                            {(customer.churn * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ),
    },

    // ------------------------
    // Product & Sales KPIs
    // ------------------------
    "total-revenue": {
      id: "total-revenue",
      title: "Total Revenue (YTD)",
      description: "Total revenue year-to-date",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: DollarSign,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Total Revenue (YTD)</CardTitle>
            <DollarSign className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtCurrency(KPI.revenueYTD)}</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="size-3 text-green-600" />
              <span className="text-green-600">
                {fmtPercent(KPI.revenueGrowth30d)}
              </span>
              <span>vs prior window</span>
            </p>
          </CardContent>
        </Card>
      ),
    },

    "avg-order-value": {
      id: "avg-order-value",
      title: "Average Order Value",
      description: "Average value per transaction",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: ShoppingCart,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Average Order Value</CardTitle>
            <ShoppingCart className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtCurrency2(KPI.aov)}</div>
            <p className="text-xs text-muted-foreground">
              Orders/week: {KPI.ordersPerWeek.toFixed(1)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    "stock-out-risk": {
      id: "stock-out-risk",
      title: "Stock-Out Risk",
      description: "SKUs at/under reorder threshold (proxy)",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: AlertTriangle,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Stock-Out Risk</CardTitle>
            <AlertTriangle className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtPercent(KPI.stockOutRiskPct, 0)}</div>
            <p className="text-xs text-muted-foreground">
              Proxy from inventory thresholds
            </p>
          </CardContent>
        </Card>
      ),
    },

    "inventory-turnover": {
      id: "inventory-turnover",
      title: "Inventory Turnover (proxy)",
      description: "Approx turnover (proxy)",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: RefreshCw,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">
              Inventory Turnover (proxy)
            </CardTitle>
            <RefreshCw className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {KPI.inventoryTurnoverProxy.toFixed(1)}x
            </div>
            <p className="text-xs text-muted-foreground">
              Based on sales + avg stock proxy
            </p>
          </CardContent>
        </Card>
      ),
    },

    // ------------------------
    // Marketing / Growth KPIs
    // ------------------------
    "conversion-rate": {
      id: "conversion-rate",
      title: "Conversion Rate",
      description: "Purchase events / relevant sessions (current definition)",
      type: "card",
      defaultSize: "small",
      category: "Marketing / Growth",
      icon: Target,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Conversion Rate</CardTitle>
            <Target className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtPercent(KPI.conversionRate)}</div>
            <p className="text-xs text-muted-foreground">
              Cart Abandon: {fmtPercent(KPI.cartAbandonmentRate)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    "cart-abandonment-rate": {
      id: "cart-abandonment-rate",
      title: "Cart Abandonment Rate",
      description: "Abandoned carts / carts (current definition)",
      type: "card",
      defaultSize: "small",
      category: "Marketing / Growth",
      icon: ShoppingCart,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Cart Abandonment</CardTitle>
            <ShoppingCart className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {fmtPercent(KPI.cartAbandonmentRate)}
            </div>
            <p className="text-xs text-muted-foreground">
              Bounce Rate: {fmtPercent(KPI.bounceRate)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    "customer-acquisition-cost": {
      id: "customer-acquisition-cost",
      title: "CAC (proxy)",
      description: "Ad spend / new customers (proxy)",
      type: "card",
      defaultSize: "small",
      category: "Marketing / Growth",
      icon: DollarSign,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">CAC (proxy)</CardTitle>
            <DollarSign className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">{fmtCurrency2(KPI.cac)}</div>
            <p className="text-xs text-muted-foreground">
              ROAS: {KPI.roas.toFixed(1)}x
            </p>
          </CardContent>
        </Card>
      ),
    },

    "campaign-roi": {
      id: "campaign-roi",
      title: "Revenue by Channel",
      description: "Revenue by marketing channel",
      type: "chart",
      defaultSize: "medium",
      category: "Marketing / Growth",
      icon: DollarSign,
      render: () => (
        <Card>
          <CardHeader>
            <CardTitle>Revenue by Channel</CardTitle>
            <CardDescription>
              Based on snapshot revenue_by_channel
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channelRevenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="channel" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="revenue" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ),
    },

    "promo-driven-revenue": {
      id: "promo-driven-revenue",
      title: "Promotion Uplift (proxy)",
      description: "Proxy uplift based on coupons/promo heuristics",
      type: "card",
      defaultSize: "small",
      category: "Marketing / Growth",
      icon: Sparkles,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Promotion Uplift (proxy)</CardTitle>
            <Sparkles className="size-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {fmtPercent(KPI.promoUpliftProxy, 2)}
            </div>
            <p className="text-xs text-muted-foreground">
              Campaign CR: {fmtPercent(KPI.campaignConversionRate)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    // "forecast-rev-30d": {
    //   id: "forecast-rev-30d",
    //   title: "Forecasted Revenue (30d)",
    //   description: "Simple run-rate forecast from recent window",
    //   type: "card",
    //   defaultSize: "small",
    //   category: "Product & Sales",
    //   icon: TrendingUp,
    //   render: () => (
    //     <Card>
    //       <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    //         <CardTitle className="text-sm">Forecasted Revenue (30d)</CardTitle>
    //         <TrendingUp className="size-4 text-teal-600" />
    //       </CardHeader>
    //       <CardContent>
    //         <div className="text-2xl">{fmtCurrency(KPI.forecastRev30d)}</div>
    //         <p className="text-xs text-muted-foreground">
    //           7d: {fmtCurrency(KPI.forecastRev7d)} • 90d:{" "}
    //           {fmtCurrency(KPI.forecastRev90d)}
    //         </p>
    //       </CardContent>
    //     </Card>
    //   ),
    // },

    "avg-margin": {
      id: "avg-margin",
      title: "Avg Product Margin",
      description: "(Retail - Cost) / Retail average",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: Percent,
      render: () => (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Avg Product Margin</CardTitle>
            <Percent className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl">
              {fmtPercent(KPI.avgProductMarginPct)}
            </div>
            <p className="text-xs text-muted-foreground">
              Return Rate (proxy): {fmtPercent(KPI.returnRateProxy)}
            </p>
          </CardContent>
        </Card>
      ),
    },

    // ------------------------
    // Forecasting & Executive Insights
    // ------------------------
    "forecast-revenue-7-30-90": {
      id: "forecast-revenue-7-30-90",
      title: "Forecasted Revenue (7/30/90)",
      description: "Projected revenue if current trends continue",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: TrendingUp,
      render: () => {
        const fr = forecastSnapshot?.forecasts?.forecasted_revenue;
        return (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Forecasted Revenue (30)</CardTitle>
              <TrendingUp className="size-4 text-teal-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {fmtCurrency(fr?.next_30d ?? KPI.forecastRev30d ?? 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                7d: {fmtCurrency(fr?.next_7d ?? KPI.forecastRev7d ?? 0)} • 90d:{" "}
                {fmtCurrency(fr?.next_90d ?? KPI.forecastRev90d ?? 0)}
              </p>
            </CardContent>
          </Card>
        );
      },
    },

    "expected-churn-next-30d": {
      id: "expected-churn-next-30d",
      title: "Expected Churn (Next 30 Days)",
      description: "Forecasted churn rate next month",
      type: "card",
      defaultSize: "small",
      category: "Customer",
      icon: AlertTriangle,
      render: () => {
        const churn = forecastSnapshot?.forecasts?.expected_churn_next_month;
        const v = churn?.expected_churn_rate_next_30d ?? 0;
        return (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">
                Expected Churn (Next 30 Days)
              </CardTitle>
              <AlertTriangle className="size-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">{fmtPercent(v)}</div>
              <p className="text-xs text-muted-foreground">
                ROC-AUC: {(churn?.metrics?.roc_auc ?? 0).toFixed(2)} • AP:{" "}
                {(churn?.metrics?.avg_precision ?? 0).toFixed(2)}
              </p>
            </CardContent>
          </Card>
        );
      },
    },

    "projected-cashflow-30d": {
      id: "projected-cashflow-30d",
      title: "Projected Cash Flow (30d)",
      description: "Proxy cashflow projection next 30 days",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: DollarSign,
      render: () => {
        const cf = forecastSnapshot?.forecasts?.projected_cashflow;
        return (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">
                Projected Cash Flow (30d)
              </CardTitle>
              <DollarSign className="size-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {fmtCurrency(cf?.next_30d_cash_proxy ?? 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                {cf?.note ?? "Proxy estimate"}
              </p>
            </CardContent>
          </Card>
        );
      },
    },

    "sku-demand-forecast-status": {
      id: "sku-demand-forecast-status",
      title: "SKU Demand Forecast Status",
      description: "Data sufficiency / readiness for SKU forecasting",
      type: "card",
      defaultSize: "small",
      category: "Product & Sales",
      icon: BarChart3,
      render: () => {
        const err =
          forecastSnapshot?.forecasts?.forecasted_demand_per_sku?.error;
        const ok = !err;
        return (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">
                SKU Demand Forecast Status
              </CardTitle>
              <BarChart3 className="size-4 text-slate-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">{ok ? "Available" : "Unavailable"}</div>
              <p className="text-xs text-muted-foreground">
                {ok ? "SKU forecast is ready" : err}
              </p>
            </CardContent>
          </Card>
        );
      },
    },

    "drivers-growth-decline": {
      id: "drivers-growth-decline",
      title: "Key Drivers of Growth / Decline",
      description: "Auto-generated drivers from recent signals",
      type: "card",
      defaultSize: "medium",
      category: "Marketing / Growth",
      icon: Sparkles,
      render: () => {
        const drivers =
          forecastSnapshot?.executive_insights?.key_drivers_of_growth_decline ??
          [];
        const top = drivers.slice(0, 6);

        const prettyDriver = (s: string) => {
          // Example:
          // "customers_features: total_spend vs monetary_value (Pearson) p_adj=0 effect=1.0"
          const [left, ...rest] = s.split(":");
          const right = rest.join(":").trim();

          const dataset = left.replace(/_/g, " ");
          const effectMatch = right.match(/effect=([0-9.]+)/);
          const effect = effectMatch ? Number(effectMatch[1]) : null;

          const methodMatch = right.match(/\(([^)]+)\)/);
          const method = methodMatch?.[1] ?? null;

          const statement = right
            .replace(/\([^)]*\)/g, "") // remove (Pearson)
            .replace(/\s*p_adj=.*$/, "") // remove p_adj=...
            .trim();

          return { dataset, statement, method, effect };
        };

        return (
          <Card>
            <CardHeader>
              <CardTitle>Key Drivers of Growth / Decline</CardTitle>
              <CardDescription>
                Auto-generated drivers from recent signals
              </CardDescription>
            </CardHeader>

            <CardContent>
              {top.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No drivers available.
                </p>
              ) : (
                <div className="space-y-2 max-h-44 overflow-auto pr-1">
                  {top.map((raw, i) => {
                    const d = prettyDriver(raw);
                    return (
                      <div
                        key={i}
                        className="rounded-md border p-2 text-sm leading-relaxed"
                      >
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">
                            {d.dataset}
                          </Badge>
                          {d.method && (
                            <Badge variant="secondary" className="text-xs">
                              {d.method}
                            </Badge>
                          )}
                          {d.effect !== null && (
                            <span className="text-xs text-muted-foreground">
                              effect {d.effect.toFixed(2)}
                            </span>
                          )}
                        </div>

                        <p className="text-muted-foreground break-words whitespace-normal">
                          {d.statement}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        );
      },
    },

    "risks-opportunities-month": {
      id: "risks-opportunities-month",
      title: "Top Risks & Opportunities (This Month)",
      description: "Executive decision support",
      type: "card",
      defaultSize: "medium",
      category: "Marketing / Growth",
      icon: AlertTriangle,
      render: () => {
        const risks = forecastSnapshot?.executive_insights?.top_3_risks ?? [];
        const opps =
          forecastSnapshot?.executive_insights?.top_3_opportunities ?? [];

        return (
          <Card>
            <CardHeader>
              <CardTitle>Top Risks & Opportunities (This Month)</CardTitle>
              <CardDescription>
                AI-generated summary for executives
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium">Risks</p>
                {risks.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No risks available.
                  </p>
                ) : (
                  <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                    {risks.slice(0, 3).map((r, i) => (
                      <li key={i} className="break-words">
                        {r.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <p className="text-sm font-medium">Opportunities</p>
                {opps.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No opportunities available.
                  </p>
                ) : (
                  <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                    {opps.slice(0, 3).map((o, i) => (
                      <li key={i} className="break-words">
                        {o.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>
        );
      },
    },
  };
}
