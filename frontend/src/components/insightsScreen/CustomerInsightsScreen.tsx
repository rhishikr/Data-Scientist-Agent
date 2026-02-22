import React, { useMemo, useState } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Skeleton } from "../ui/skeleton";
import { Button } from "../ui/button";

import {
  LayoutDashboard,
  DollarSign,
  Package,
  Users,
  ShoppingBag,
  Megaphone,
  Sparkles,
} from "lucide-react";

import {
  useDashboardData,
  useInsightsData,
  useRevenueForecastSeries,
  useDemandForecast,
  useChurnPredictions,
  useAiAnalysis,
} from "./dashboard/data";
import {
  clamp01,
  getCardValue,
  safeNum,
  fmtCurrency2,
} from "./dashboard/formatters";
import { RunSelector } from "./RunSelector";

import { KpiStrip } from "./sections/KpiStrip";
import { OverviewTab } from "./sections/OverviewTab";
import { RevenueSalesTab } from "./sections/RevenueSalesTab";
import { StockDemandTab } from "./sections/StockDemandTab";
import { CustomersTab } from "./sections/CustomersTab";
import { ProductsTab } from "./sections/ProductsTab";
import { MarketingTab } from "./sections/MarketingTab";
import { AiInsightsTab } from "./sections/AiInsightsTab";

export function CustomerInsightsScreen() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Existing data hooks
  const {
    snapshot,
    cards,
    customers,
    loading,
    error,
    refresh,
    forecastSnapshot,
  } = useDashboardData(selectedRunId);

  // New data hooks
  const { data: insightsData, loading: insightsLoading } =
    useInsightsData(selectedRunId);
  const { series: revenueSeries, loading: revenueLoading } =
    useRevenueForecastSeries(selectedRunId);
  const { skus: demandSkus, loading: demandLoading } =
    useDemandForecast(selectedRunId);
  const { customers: churnPredictions, loading: churnLoading } =
    useChurnPredictions(selectedRunId);
  const { data: aiAnalysis, loading: aiAnalysisLoading } =
    useAiAnalysis(selectedRunId);

  // Derive channel revenue data from KPI snapshot
  const channelRevenueData = useMemo(() => {
    const revenueByChannel =
      snapshot?.kpis?.marketing_effectiveness?.revenue_by_channel ?? {};
    const entries = Object.entries(revenueByChannel);
    return entries.map(([channel, revenue]) => ({
      channel,
      revenue: safeNum(revenue, 0),
    }));
  }, [snapshot]);

  // Extract insights array
  const insights = useMemo(() => {
    if (!insightsData) return [];
    if (Array.isArray(insightsData)) return insightsData;
    if (Array.isArray((insightsData as any)?.insights))
      return (insightsData as any).insights;
    return [];
  }, [insightsData]);

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-64 mb-2" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-10 w-48" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-96 rounded-lg" />
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
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Insights & Predictions</h1>
            <p className="text-xs text-muted-foreground">
              AI-powered retail analytics dashboard
            </p>
          </div>
          <RunSelector
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
          />
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
      {/* KPI Strip */}
      <KpiStrip cards={cards} />

      {/* Tabbed Content */}
      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">
            <LayoutDashboard className="size-4 mr-1.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="revenue">
            <DollarSign className="size-4 mr-1.5" />
            Revenue & Sales
          </TabsTrigger>
          <TabsTrigger value="stock">
            <Package className="size-4 mr-1.5" />
            Stock & Demand
          </TabsTrigger>
          <TabsTrigger value="customers">
            <Users className="size-4 mr-1.5" />
            Customers
          </TabsTrigger>
          <TabsTrigger value="products">
            <ShoppingBag className="size-4 mr-1.5" />
            Products
          </TabsTrigger>
          <TabsTrigger value="marketing">
            <Megaphone className="size-4 mr-1.5" />
            Marketing
          </TabsTrigger>
          <TabsTrigger value="insights">
            <Sparkles className="size-4 mr-1.5" />
            AI Insights
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab
            cards={cards}
            revenueSeries={revenueSeries}
            channelRevenueData={channelRevenueData}
            insights={insights}
            forecastSnapshot={forecastSnapshot}
            demandSkus={demandSkus}
          />
        </TabsContent>

        <TabsContent value="revenue">
          <RevenueSalesTab
            cards={cards}
            revenueSeries={revenueSeries}
            channelRevenueData={channelRevenueData}
            forecastSnapshot={forecastSnapshot}
          />
        </TabsContent>

        <TabsContent value="stock">
          <StockDemandTab cards={cards} demandSkus={demandSkus} />
        </TabsContent>

        <TabsContent value="customers">
          <CustomersTab
            cards={cards}
            customers={customers}
            churnPredictions={churnPredictions}
          />
        </TabsContent>

        <TabsContent value="products">
          <ProductsTab cards={cards} snapshot={snapshot} />
        </TabsContent>

        <TabsContent value="marketing">
          <MarketingTab
            cards={cards}
            channelRevenueData={channelRevenueData}
            forecastSnapshot={forecastSnapshot}
          />
        </TabsContent>

        <TabsContent value="insights">
          <AiInsightsTab
            insights={insights}
            forecastSnapshot={forecastSnapshot}
            aiAnalysis={aiAnalysis}
            aiAnalysisLoading={aiAnalysisLoading}
          />
        </TabsContent>
      </Tabs>
      </div>
    </div>
  );
}
