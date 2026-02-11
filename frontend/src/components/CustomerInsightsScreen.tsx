import React, { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "./ui/sheet";
import { Input } from "./ui/input";
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
  Users,
  TrendingUp,
  AlertTriangle,
  GripVertical,
  X,
  Plus,
  Settings2,
  Search,
  BarChart3,
  ShoppingCart,
  DollarSign,
  Target,
  Percent,
  ChevronUp,
  ChevronDown,
  UserCheck,
  UserPlus,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import kpiSnapshot from "../../../backend/data/kpi_outputs/kpi_snapshot.json";
import cardsJson from "../../../backend/data/kpi_outputs/cards.json";
import customersJson from "../../../backend/data/kpi_outputs/customers.json";
import productsJson from "../../../backend/data/kpi_outputs/products.json";

// -----------------------------
// Types (lightweight)
// -----------------------------
type KpiCardRow = {
  id: string;
  title: string;
  value: number;
  unit?: string;
  format?: "currency" | "percent" | "number" | "minutes";
  group?: string;
};

type CustomerRow = {
  customer_id: string;
  name: string;
  location?: string;
  device_type?: string;
  total_orders: number;
  total_spend: number;
  avg_order_value?: number;
  recency_days?: number;
  top_product_id?: string;
};

type Snapshot = {
  meta?: {
    generated_at?: string;
    as_of?: string;
    datasets_used?: string[];
  };
  kpis?: any;
};

// -----------------------------
// Helpers
// -----------------------------
const fmtCurrency = (n: number) =>
  `$${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })}`;

const fmtCurrency2 = (n: number) =>
  `$${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  })}`;

const fmtPercent = (n: number, digits = 1) =>
  `${((Number.isFinite(n) ? n : 0) * 100).toFixed(digits)}%`;

const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

const safeNum = (v: any, fallback = 0) =>
  Number.isFinite(Number(v)) ? Number(v) : fallback;

const getCardValue = (cards: KpiCardRow[], id: string, fallback = 0) => {
  const row = cards.find((c) => c.id === id);
  return row ? safeNum(row.value, fallback) : fallback;
};

const getAsOfLabel = (snap: Snapshot) => {
  const raw = snap?.meta?.as_of ?? "";
  if (!raw) return "";
  return raw.split(".")[0];
};

type WidgetSize = "small" | "medium" | "large";
type WidgetType = "card" | "chart" | "table";
type WidgetCategory = "Customer" | "Product & Sales" | "Marketing / Growth";

interface WidgetDefinition {
  id: string;
  title: string;
  description: string;
  type: WidgetType;
  defaultSize: WidgetSize;
  category: WidgetCategory;
  icon: any;
  render: () => React.ReactNode;
}

// =====================================================
// Widget wrapper component (unchanged)
// =====================================================
function DashboardWidget({
  children,
  isCustomizing,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  className = "",
}: {
  children: React.ReactNode;
  isCustomizing: boolean;
  onRemove?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
  className?: string;
}) {
  return (
    <div className={`relative group ${className}`}>
      {isCustomizing && (
        <>
          <div className="absolute -left-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <div className="bg-slate-200 rounded p-1 shadow-sm">
              <GripVertical className="size-4 text-slate-600" />
            </div>
          </div>

          <button
            onClick={onRemove}
            className="absolute -right-2 -top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 hover:bg-red-600 text-white rounded-full p-1 shadow-md z-10"
            title="Remove widget"
          >
            <X className="size-3" />
          </button>

          <div className="absolute -right-2 top-8 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-1 z-10">
            {canMoveUp && (
              <button
                onClick={onMoveUp}
                className="bg-teal-500 hover:bg-teal-600 text-white rounded-full p-1 shadow-md"
                title="Move up"
              >
                <ChevronUp className="size-3" />
              </button>
            )}
            {canMoveDown && (
              <button
                onClick={onMoveDown}
                className="bg-teal-500 hover:bg-teal-600 text-white rounded-full p-1 shadow-md"
                title="Move down"
              >
                <ChevronDown className="size-3" />
              </button>
            )}
          </div>

          <div className="absolute inset-0 border-2 border-dashed border-teal-300 rounded-lg pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity" />
        </>
      )}
      {children}
    </div>
  );
}

export function CustomerInsightsScreen() {
  const [isCustomizing, setIsCustomizing] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // ✅ JSON data (imported)
  const snapshot = kpiSnapshot as unknown as Snapshot;
  const cards = cardsJson as unknown as KpiCardRow[];
  const customers = customersJson as unknown as CustomerRow[];
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const products = productsJson as unknown as any[];

  const asOfLabel = useMemo(() => getAsOfLabel(snapshot), [snapshot]);

  const KPI = useMemo(() => {
    const revenueByChannel =
      snapshot?.kpis?.marketing_effectiveness?.revenue_by_channel ?? {};

    return {
      asOf: asOfLabel || "N/A",

      // Revenue & Sales Health
      revenueMTD: getCardValue(cards, "rev_mtd", 0),
      revenueQTD: getCardValue(cards, "rev_qtd", 0),
      revenueYTD: getCardValue(cards, "rev_ytd", 0),
      revenueGrowth30d: getCardValue(cards, "rev_growth_30d", 0),
      aov: getCardValue(cards, "aov", 0),
      ordersPerDay: getCardValue(cards, "orders_day", 0),
      ordersPerWeek: getCardValue(cards, "orders_week", 0),

      // Customer Health
      activeCustomers30d: getCardValue(cards, "active_customers_30d", 0),
      newCustomers30d: getCardValue(cards, "new_customers_30d", 0),
      returningCustomers30d: getCardValue(cards, "returning_customers_30d", 0),
      repeatPurchaseRate: getCardValue(cards, "repeat_purchase_rate", 0),
      retentionRateProxy: getCardValue(cards, "retention_rate_proxy", 0),
      churnRateProxy: getCardValue(cards, "churn_rate_proxy", 0),
      avgClv: getCardValue(cards, "avg_clv", 0),

      // Funnel
      conversionRate: getCardValue(cards, "conversion_rate", 0),
      cartAbandonmentRate: getCardValue(cards, "cart_abandonment_rate", 0),
      bounceRate: getCardValue(cards, "bounce_rate", 0),
      avgTimeToPurchaseMin: getCardValue(cards, "time_to_purchase", 0),
      checkoutCompletionRateRaw: getCardValue(
        cards,
        "checkout_completion_rate",
        0,
      ),

      // Marketing
      cac: getCardValue(cards, "cac", 0),
      roas: getCardValue(cards, "roas", 0),
      campaignConversionRate: getCardValue(cards, "campaign_cr", 0),
      promoUpliftProxy: getCardValue(cards, "promo_uplift", 0),
      revenueByChannel: revenueByChannel as Record<string, number>,

      // Product & Merchandising
      avgProductMarginPct: getCardValue(cards, "avg_margin_pct", 0),
      returnRateProxy: getCardValue(cards, "return_rate_proxy", 0),

      // Inventory & Operations
      stockOutRiskPct: getCardValue(cards, "stock_out_risk_pct", 0),
      inventoryTurnoverProxy: getCardValue(
        cards,
        "inventory_turnover_proxy",
        0,
      ),

      // Forecast
      forecastRev7d: getCardValue(cards, "forecast_rev_7d", 0),
      forecastRev30d: getCardValue(cards, "forecast_rev_30d", 0),
      forecastRev90d: getCardValue(cards, "forecast_rev_90d", 0),
    };
  }, [cards, snapshot, asOfLabel]);

  const channelRevenueData = useMemo(() => {
    const entries = Object.entries(KPI.revenueByChannel ?? {});
    return entries.map(([channel, revenue]) => ({
      channel,
      revenue: safeNum(revenue, 0),
    }));
  }, [KPI.revenueByChannel]);

  const topCustomers = useMemo(() => {
    const sorted = [...(customers || [])].sort(
      (a, b) => safeNum(b.total_spend) - safeNum(a.total_spend),
    );

    const top = sorted.slice(0, 12);

    const maxRecency = Math.max(
      1,
      ...top.map((c) => safeNum(c.recency_days, 0)),
    );

    const segmentFromSpend = (spend: number) => {
      if (spend >= 3500) return "Top Buyer";
      if (spend >= 1500) return "Moderate";
      return "At-Risk";
    };

    return top.map((c) => {
      const recencyDays = safeNum(c.recency_days, 0);
      const churn = clamp01(recencyDays / maxRecency);

      return {
        id: c.customer_id,
        name: c.name,
        segment: segmentFromSpend(safeNum(c.total_spend)),
        recency: `${recencyDays} days`,
        frequency: safeNum(c.total_orders, 0),
        monetary: fmtCurrency2(safeNum(c.total_spend, 0)),
        churn,
      };
    });
  }, [customers]);

  // =====================================================
  // Widget Registry
  // ✅ Removed hardcoded "demo" widgets:
  //   - customer-lifetime-value (LineChart demo)
  //   - customer-segments (PieChart demo)
  // =====================================================
  const widgetRegistry: Record<string, WidgetDefinition> = useMemo(
    () => ({
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
              <p className="text-xs text-muted-foreground">As of {KPI.asOf}</p>
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
              <div className="text-2xl">
                {fmtPercent(KPI.retentionRateProxy)}
              </div>
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
              <p className="text-xs text-muted-foreground">As of {KPI.asOf}</p>
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
              <CardDescription>
                Spend + orders + recency (from your JSON)
              </CardDescription>
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
              <div className="text-2xl">
                {fmtPercent(KPI.stockOutRiskPct, 0)}
              </div>
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
              <CardTitle className="text-sm">
                Promotion Uplift (proxy)
              </CardTitle>
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

      "forecast-rev-30d": {
        id: "forecast-rev-30d",
        title: "Forecasted Revenue (30d)",
        description: "Simple run-rate forecast from recent window",
        type: "card",
        defaultSize: "small",
        category: "Product & Sales",
        icon: TrendingUp,
        render: () => (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">
                Forecasted Revenue (30d)
              </CardTitle>
              <TrendingUp className="size-4 text-teal-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">{fmtCurrency(KPI.forecastRev30d)}</div>
              <p className="text-xs text-muted-foreground">
                7d: {fmtCurrency(KPI.forecastRev7d)} • 90d:{" "}
                {fmtCurrency(KPI.forecastRev90d)}
              </p>
            </CardContent>
          </Card>
        ),
      },

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
    }),
    [KPI, channelRevenueData, topCustomers],
  );

  // ✅ Updated default widgets: removed demo chart widgets
  const [selectedWidgets, setSelectedWidgets] = useState<string[]>([
    "total-revenue",
    "avg-order-value",
    "conversion-rate",
    "customer-acquisition-cost",
    "active-customers",
    "avg-customer-value",
    "stock-out-risk",
    "forecast-rev-30d",
    "top-customers",
  ]);

  const handleAddWidget = (widgetId: string) => {
    if (selectedWidgets.includes(widgetId)) return;
    setSelectedWidgets([...selectedWidgets, widgetId]);
  };

  const handleRemoveWidget = (widgetId: string) => {
    setSelectedWidgets(selectedWidgets.filter((id) => id !== widgetId));
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newWidgets = [...selectedWidgets];
    [newWidgets[index - 1], newWidgets[index]] = [
      newWidgets[index],
      newWidgets[index - 1],
    ];
    setSelectedWidgets(newWidgets);
  };

  const handleMoveDown = (index: number) => {
    if (index === selectedWidgets.length - 1) return;
    const newWidgets = [...selectedWidgets];
    [newWidgets[index], newWidgets[index + 1]] = [
      newWidgets[index + 1],
      newWidgets[index],
    ];
    setSelectedWidgets(newWidgets);
  };

  const catalogCategories = useMemo(() => {
    return Object.values(widgetRegistry).reduce(
      (acc, widget) => {
        if (!acc[widget.category]) acc[widget.category] = [];
        acc[widget.category].push(widget);
        return acc;
      },
      {} as Record<string, WidgetDefinition[]>,
    );
  }, [widgetRegistry]);

  const filteredCatalog = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return Object.entries(catalogCategories)
      .map(([category, widgets]) => ({
        category,
        widgets: widgets.filter(
          (w) =>
            w.title.toLowerCase().includes(q) ||
            w.description.toLowerCase().includes(q),
        ),
      }))
      .filter((cat) => cat.widgets.length > 0);
  }, [catalogCategories, searchQuery]);

  const renderWidget = (widgetId: string, index: number) => {
    const widget = widgetRegistry[widgetId];
    if (!widget) return null;

    const gridClass =
      widget.defaultSize === "small"
        ? "col-span-1"
        : widget.defaultSize === "medium"
          ? "md:col-span-2"
          : "md:col-span-4";

    return (
      <DashboardWidget
        key={widgetId}
        isCustomizing={isCustomizing}
        onRemove={() => handleRemoveWidget(widgetId)}
        onMoveUp={() => handleMoveUp(index)}
        onMoveDown={() => handleMoveDown(index)}
        canMoveUp={index > 0}
        canMoveDown={index < selectedWidgets.length - 1}
        className={gridClass}
      >
        {widget.render()}
      </DashboardWidget>
    );
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mb-2">Insights and Predictions</h1>
            <p className="text-muted-foreground">
              AI-powered analytics • Snapshot as of{" "}
              <span className="font-medium">{KPI.asOf}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Select defaultValue="30">
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Date range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="365">Last year</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant={isCustomizing ? "default" : "outline"}
              onClick={() => setIsCustomizing(!isCustomizing)}
              className={isCustomizing ? "bg-teal-600 hover:bg-teal-700" : ""}
            >
              <Settings2 className="size-4 mr-2" />
              {isCustomizing ? "Done Customizing" : "Customize Dashboard"}
            </Button>
          </div>
        </div>

        {isCustomizing && (
          <Card className="bg-teal-50 border-teal-200">
            <CardContent className="py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-teal-600 text-white rounded-full p-1.5">
                    <Settings2 className="size-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-teal-900">
                      Customization Mode Active
                    </p>
                    <p className="text-xs text-teal-700">
                      Use ↑↓ arrows to reorder, ✕ to remove, or add new KPIs
                    </p>
                  </div>
                </div>
                <Button
                  onClick={() => setCatalogOpen(true)}
                  className="bg-teal-600 hover:bg-teal-700"
                >
                  <Plus className="size-4 mr-2" />
                  Add KPI
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 md:grid-cols-4">
          {selectedWidgets.map((widgetId, index) =>
            renderWidget(widgetId, index),
          )}
        </div>

        {selectedWidgets.length === 0 && (
          <Card className="py-12">
            <CardContent className="text-center">
              <BarChart3 className="size-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <h3 className="font-semibold mb-2">No widgets on dashboard</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Click "Customize Dashboard" and add KPIs to get started
              </p>
              <Button
                onClick={() => {
                  setIsCustomizing(true);
                  setCatalogOpen(true);
                }}
                className="bg-teal-600 hover:bg-teal-700"
              >
                <Plus className="size-4 mr-2" />
                Add Your First KPI
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* KPI Catalog Drawer */}
      <Sheet open={catalogOpen} onOpenChange={setCatalogOpen}>
        <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Add KPI to Dashboard</SheetTitle>
            <SheetDescription>
              Browse and add analytics KPIs to customize your dashboard
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                placeholder="Search KPIs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          <div className="space-y-6">
            {filteredCatalog.map(({ category, widgets }) => (
              <div key={category}>
                <h3 className="font-semibold mb-3 text-sm text-muted-foreground uppercase tracking-wide">
                  {category}
                </h3>
                <div className="space-y-2">
                  {widgets.map((widget) => {
                    const Icon = widget.icon;
                    const isAdded = selectedWidgets.includes(widget.id);
                    return (
                      <Card
                        key={widget.id}
                        className={`hover:border-teal-300 transition-colors ${
                          isAdded ? "bg-slate-50 border-slate-300" : ""
                        }`}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-3 flex-1">
                              <div
                                className={`rounded p-2 mt-0.5 ${
                                  isAdded ? "bg-slate-200" : "bg-teal-50"
                                }`}
                              >
                                <Icon
                                  className={`size-4 ${
                                    isAdded ? "text-slate-600" : "text-teal-600"
                                  }`}
                                />
                              </div>
                              <div className="flex-1">
                                <h4 className="font-medium text-sm mb-1">
                                  {widget.title}
                                </h4>
                                <p className="text-xs text-muted-foreground mb-2">
                                  {widget.description}
                                </p>
                                <Badge variant="outline" className="text-xs">
                                  {widget.type}
                                </Badge>
                              </div>
                            </div>
                            {isAdded ? (
                              <Badge variant="secondary" className="shrink-0">
                                Added
                              </Badge>
                            ) : (
                              <Button
                                size="sm"
                                className="bg-teal-600 hover:bg-teal-700 shrink-0"
                                onClick={() => handleAddWidget(widget.id)}
                              >
                                <Plus className="size-4" />
                              </Button>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {filteredCatalog.length === 0 && (
            <div className="text-center py-12">
              <Search className="size-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-sm text-muted-foreground">
                No KPIs found matching "{searchQuery}"
              </p>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
