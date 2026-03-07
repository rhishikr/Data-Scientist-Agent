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
  RefreshCw,
  ServerOff,
  ClipboardList,
} from "lucide-react";
import { Card, CardContent } from "../ui/card";

import {
  useDashboardData,
  useInsightsData,
  useRevenueForecastSeries,
  useDemandForecast,
  useChurnPredictions,
  useAiAnalysis,
  useActionPlan,
  useChartNarratives,
  useLocationStock,
} from "./dashboard/data";
import {
  clamp01,
  getCardValue,
  safeNum,
  fmtCurrency2,
} from "./dashboard/formatters";
import { RunSelector } from "./RunSelector";

import { DiagnosisBanner } from "./sections/DiagnosisBanner";
import { ActionQueueTab } from "./sections/ActionQueueTab";
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
  const { data: actionPlan, loading: actionPlanLoading } =
    useActionPlan(selectedRunId);
  const { data: chartNarratives } = useChartNarratives(selectedRunId);
  const { locations: locationSummary, transfers: storeTransfers } =
    useLocationStock(selectedRunId);

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
      <div>
        <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">Insights & Predictions</h1>
              <p className="text-xs text-muted-foreground">
                AI-powered retail analytics dashboard
              </p>
            </div>
            <Skeleton className="h-10 w-48 rounded-lg" />
          </div>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-10 w-full rounded-xl" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Skeleton className="h-72 rounded-xl lg:col-span-2" />
            <Skeleton className="h-72 rounded-xl" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Skeleton className="h-32 rounded-xl" />
            <Skeleton className="h-32 rounded-xl" />
            <Skeleton className="h-32 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
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
        <div className="p-6 flex items-center justify-center min-h-[60vh]">
          <Card className="max-w-md w-full">
            <CardContent className="pt-6 pb-6 flex flex-col items-center text-center gap-4">
              <div className="rounded-full bg-red-50 p-4">
                <ServerOff className="size-8 text-red-500" />
              </div>
              <div>
                <h2 className="text-lg font-semibold mb-1">Unable to load dashboard</h2>
                <p className="text-sm text-muted-foreground">
                  {error.includes("fetch")
                    ? "Could not connect to the backend server. Make sure the API server is running."
                    : error}
                </p>
              </div>
              <Button onClick={refresh} className="bg-teal-600 hover:bg-teal-700 gap-2">
                <RefreshCw className="size-4" />
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
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
      {/* Diagnosis Banner */}
      <DiagnosisBanner cards={cards} actionPlan={actionPlan} />

      {/* Tabbed Content */}
      <Tabs defaultValue="actions">
        <TabsList className="w-full">
          <TabsTrigger value="actions" className="flex-1">
            <ClipboardList className="size-4 mr-1.5" />
            Action Plan
          </TabsTrigger>
          <TabsTrigger value="insights" className="flex-1">
            <Sparkles className="size-4 mr-1.5" />
            AI Insights
          </TabsTrigger>
          <TabsTrigger value="overview" className="flex-1">
            <LayoutDashboard className="size-4 mr-1.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="revenue" className="flex-1">
            <DollarSign className="size-4 mr-1.5" />
            Revenue & Sales
          </TabsTrigger>
          <TabsTrigger value="stock" className="flex-1">
            <Package className="size-4 mr-1.5" />
            Stock & Demand
          </TabsTrigger>
          <TabsTrigger value="customers" className="flex-1">
            <Users className="size-4 mr-1.5" />
            Customers
          </TabsTrigger>
          <TabsTrigger value="products" className="flex-1">
            <ShoppingBag className="size-4 mr-1.5" />
            Products
          </TabsTrigger>
          <TabsTrigger value="marketing" className="flex-1">
            <Megaphone className="size-4 mr-1.5" />
            Marketing
          </TabsTrigger>
        </TabsList>

        <TabsContent value="actions">
          <ActionQueueTab
            actionPlan={actionPlan}
            loading={actionPlanLoading}
            runId={selectedRunId}
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
            chartNarrative={chartNarratives?.narratives?.revenue_trend}
          />
        </TabsContent>

        <TabsContent value="stock">
          <StockDemandTab
            cards={cards}
            demandSkus={demandSkus}
            chartNarrative={chartNarratives?.narratives?.stock_health}
            locationSummary={locationSummary}
            storeTransfers={storeTransfers}
          />
        </TabsContent>

        <TabsContent value="customers">
          <CustomersTab
            cards={cards}
            customers={customers}
            churnPredictions={churnPredictions}
            chartNarrative={chartNarratives?.narratives?.churn_distribution}
            segmentRecommendations={actionPlan?.segment_recommendations}
          />
        </TabsContent>

        <TabsContent value="products">
          <ProductsTab cards={cards} snapshot={snapshot} demandSkus={demandSkus} />
        </TabsContent>

        <TabsContent value="marketing">
          <MarketingTab
            cards={cards}
            channelRevenueData={channelRevenueData}
            forecastSnapshot={forecastSnapshot}
          />
        </TabsContent>

      </Tabs>
      </div>
    </div>
  );
}
