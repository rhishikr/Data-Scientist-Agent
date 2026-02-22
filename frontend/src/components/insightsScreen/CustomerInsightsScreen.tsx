import React, { useMemo, useState } from "react";

import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "../ui/sheet";
import { Input } from "../ui/input";

import { Settings2, Search, Plus, BarChart3 } from "lucide-react";

import { useDashboardData } from "./dashboard/data";
import { DashboardWidget } from "./dashboard/DashboardWidget";
import { buildWidgetRegistry } from "./dashboard/widgetRegistry";
import {
  clamp01,
  getAsOfLabel,
  getCardValue,
  safeNum,
  fmtCurrency2,
} from "./dashboard/formatters";
import { RunSelector } from "./RunSelector";

export function CustomerInsightsScreen() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const {
    snapshot,
    cards,
    customers,
    loading,
    error,
    refresh,
    forecastSnapshot,
  } = useDashboardData(selectedRunId);

  const [isCustomizing, setIsCustomizing] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const asOfLabel = useMemo(
    () => getAsOfLabel(snapshot ?? ({} as any)),
    [snapshot],
  );

  const KPI = useMemo(() => {
    const revenueByChannel =
      snapshot?.kpis?.marketing_effectiveness?.revenue_by_channel ?? {};

    return {
      asOf: asOfLabel || "N/A",

      revenueMTD: getCardValue(cards, "rev_mtd", 0),
      revenueQTD: getCardValue(cards, "rev_qtd", 0),
      revenueYTD: getCardValue(cards, "rev_ytd", 0),
      revenueGrowth30d: getCardValue(cards, "rev_growth_30d", 0),
      aov: getCardValue(cards, "aov", 0),
      ordersPerDay: getCardValue(cards, "orders_day", 0),
      ordersPerWeek: getCardValue(cards, "orders_week", 0),

      activeCustomers30d: getCardValue(cards, "active_customers_30d", 0),
      newCustomers30d: getCardValue(cards, "new_customers_30d", 0),
      returningCustomers30d: getCardValue(cards, "returning_customers_30d", 0),
      repeatPurchaseRate: getCardValue(cards, "repeat_purchase_rate", 0),
      retentionRateProxy: getCardValue(cards, "retention_rate_proxy", 0),
      churnRateProxy: getCardValue(cards, "churn_rate_proxy", 0),
      avgClv: getCardValue(cards, "avg_clv", 0),

      conversionRate: getCardValue(cards, "conversion_rate", 0),
      cartAbandonmentRate: getCardValue(cards, "cart_abandonment_rate", 0),
      bounceRate: getCardValue(cards, "bounce_rate", 0),
      avgTimeToPurchaseMin: getCardValue(cards, "time_to_purchase", 0),
      checkoutCompletionRateRaw: getCardValue(
        cards,
        "checkout_completion_rate",
        0,
      ),

      cac: getCardValue(cards, "cac", 0),
      roas: getCardValue(cards, "roas", 0),
      campaignConversionRate: getCardValue(cards, "campaign_cr", 0),
      promoUpliftProxy: getCardValue(cards, "promo_uplift", 0),
      revenueByChannel: revenueByChannel as Record<string, number>,

      avgProductMarginPct: getCardValue(cards, "avg_margin_pct", 0),
      returnRateProxy: getCardValue(cards, "return_rate_proxy", 0),

      stockOutRiskPct: getCardValue(cards, "stock_out_risk_pct", 0),
      inventoryTurnoverProxy: getCardValue(
        cards,
        "inventory_turnover_proxy",
        0,
      ),

      forecastRev7d: getCardValue(cards, "forecast_rev_7d", 0),
      forecastRev30d: getCardValue(cards, "forecast_rev_30d", 0),
      forecastRev90d: getCardValue(cards, "forecast_rev_90d", 0),
    };
  }, [snapshot, asOfLabel, cards]);

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
        name: c.name ?? "Unknown",
        segment: segmentFromSpend(safeNum(c.total_spend)),
        recency: `${recencyDays} days`,
        frequency: safeNum(c.total_orders, 0),
        monetary: fmtCurrency2(safeNum(c.total_spend, 0)),
        churn,
      };
    });
  }, [customers]);

  const widgetRegistry = useMemo(
    () =>
      buildWidgetRegistry({
        KPI,
        channelRevenueData,
        topCustomers,
        forecastSnapshot,
      }),
    [KPI, channelRevenueData, topCustomers],
  );

  const [selectedWidgets, setSelectedWidgets] = useState<string[]>([
    "total-revenue",
    "avg-order-value",
    "conversion-rate",
    "customer-acquisition-cost",
    "active-customers",
    "avg-customer-value",
    "stock-out-risk",
    "forecast-revenue-7-30-90",
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
      (acc, widget: any) => {
        if (!acc[widget.category]) acc[widget.category] = [];
        acc[widget.category].push(widget);
        return acc;
      },
      {} as Record<string, any[]>,
    );
  }, [widgetRegistry]);

  const filteredCatalog = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return Object.entries(catalogCategories)
      .map(([category, widgets]) => ({
        category,
        widgets: widgets.filter(
          (w: any) =>
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

  if (loading) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Loading dashboard…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 space-y-3">
        <p className="text-sm text-red-600">Failed to load: {error}</p>
        <Button onClick={refresh} className="bg-teal-600 hover:bg-teal-700">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mb-2">Insights and Predictions</h1>
            {/* <p className="text-muted-foreground">
              AI-powered analytics • Snapshot as of{" "}
              <span className="font-medium">{KPI.asOf}</span>
            </p> */}
          </div>

          <div className="flex items-center gap-3">
            <RunSelector
              selectedRunId={selectedRunId}
              onSelectRun={setSelectedRunId}
            />

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
            {filteredCatalog.map(({ category, widgets }: any) => (
              <div key={category}>
                <h3 className="font-semibold mb-3 text-sm text-muted-foreground uppercase tracking-wide">
                  {category}
                </h3>
                <div className="space-y-2">
                  {widgets.map((widget: any) => {
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
