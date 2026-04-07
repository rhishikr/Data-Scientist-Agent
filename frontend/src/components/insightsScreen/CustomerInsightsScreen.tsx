import React, { useEffect, useMemo, useState } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Skeleton } from "../ui/skeleton";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";

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
  MousePointerClick,
  GitCompareArrows,
  BarChart3,
  Brain,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "../ui/card";
import { API_BASE, apiFetch } from "../../lib/api";

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
  useFunnelSnapshot,
  useSessionsAnalytics,
  useRunComparison,
  useComparisonAiAnalysis,
  useRuns,
  useCampaignPerformance,
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
import { FunnelSessionsTab } from "./sections/FunnelSessionsTab";
import { RunComparisonTab } from "./sections/RunComparisonTab";

const AGENT_LABELS: Record<string, string> = {
  cleaning: "Data Cleaning",
  features: "Feature Engineering",
  hypothesis: "Hypothesis Testing",
  insights: "Insights Generation",
  kpi: "KPI Snapshot",
  forecast: "Forecasting",
  actions: "Action Plan",
};
const AGENT_ORDER = ["cleaning", "features", "hypothesis", "insights", "kpi", "forecast", "actions"];

export function CustomerInsightsScreen() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [compareWithRunId, setCompareWithRunId] = useState<string | null>(null);
  const [compareEnabled, setCompareEnabled] = useState(false);

  // Pipeline running state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelinePartial, setPipelinePartial] = useState<Record<string, any>>({});
  const [pipelineCurrentAgent, setPipelineCurrentAgent] = useState<string | null>(null);

  // Check pipeline status on mount and poll while running
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const checkStatus = async () => {
      try {
        const r = await apiFetch(`${API_BASE}/api/pipeline/status`);
        const data = await r.json();
        if (data.running) {
          setPipelineRunning(true);
          setPipelinePartial(data.partial || {});
          setPipelineCurrentAgent(data.current_agent || null);
        } else {
          setPipelineRunning(false);
          setPipelinePartial({});
          setPipelineCurrentAgent(null);
          if (interval) clearInterval(interval);
        }
      } catch {
        // Ignore errors
      }
    };

    checkStatus();
    interval = setInterval(checkStatus, 4000);
    return () => { if (interval) clearInterval(interval); };
  }, []);

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
  const { data: funnelSnapshot } = useFunnelSnapshot(selectedRunId);
  const { data: sessionsAnalytics } = useSessionsAnalytics(selectedRunId);
  const { data: runComparison, loading: comparisonLoading } =
    useRunComparison(selectedRunId, compareWithRunId, compareEnabled);
  const { data: comparisonAi, loading: comparisonAiLoading } =
    useComparisonAiAnalysis(selectedRunId, compareWithRunId, compareEnabled);
  const { runs } = useRuns();
  const { data: campaignPerformance } = useCampaignPerformance(selectedRunId);

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

  // Show pipeline-generating UI only when running AND no specific completed run is selected
  const showPipelineRunningUI = pipelineRunning && selectedRunId === null;

  if (showPipelineRunningUI) {
    const completedCount = Object.keys(pipelinePartial).length;
    const totalAgents = AGENT_ORDER.length;
    const overallProgress = Math.round((completedCount / totalAgents) * 100);

    return (
      <div>
        <div className="sticky top-0 z-20 bg-white border-b px-6 py-4">
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

        <div className="p-6 flex items-center justify-center min-h-[70vh]">
          <div className="max-w-lg w-full space-y-8">
            {/* Main status card */}
            <Card className="border-2 border-blue-100 shadow-lg">
              <CardContent className="pt-8 pb-8 flex flex-col items-center text-center gap-5">
                <div className="relative">
                  <div className="rounded-full bg-gradient-to-br from-blue-100 to-teal-100 p-5">
                    <Brain className="size-10 text-blue-600 animate-pulse" />
                  </div>
                </div>
                <div>
                  <h2 className="text-lg font-semibold mb-1">
                    Generating AI Insights & Predictions
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    The multi-agent pipeline is analyzing your data. Insights will
                    appear here once processing is complete.
                  </p>
                </div>

                {/* Progress bar */}
                <div className="w-full space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Overall progress</span>
                    <span className="font-medium">
                      {completedCount} of {totalAgents} agents complete
                    </span>
                  </div>
                  <Progress value={overallProgress} className="h-2" />
                </div>
              </CardContent>
            </Card>

            {/* Agent list */}
            <div className="space-y-2">
              {AGENT_ORDER.map((agentId) => {
                const isCompleted = agentId in pipelinePartial;
                const isRunning = pipelineCurrentAgent === agentId;

                return (
                  <div
                    key={agentId}
                    className={`flex items-center gap-3 rounded-md border px-4 py-3 transition-all ${
                      isRunning
                        ? "border-blue-200 bg-blue-50"
                        : isCompleted
                          ? "border-green-100 bg-green-50/50"
                          : "border-slate-100 bg-slate-50/50"
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="size-4 text-green-600 shrink-0" />
                    ) : isRunning ? (
                      <Loader2 className="size-4 text-blue-600 animate-spin shrink-0" />
                    ) : (
                      <div className="size-4 rounded-full border-2 border-slate-300 shrink-0" />
                    )}
                    <span
                      className={`text-sm ${
                        isRunning
                          ? "font-medium text-blue-700"
                          : isCompleted
                            ? "text-green-700"
                            : "text-muted-foreground"
                      }`}
                    >
                      {AGENT_LABELS[agentId] || agentId}
                    </span>
                    {isRunning && (
                      <span className="ml-auto text-xs text-blue-500 animate-pulse">
                        Processing...
                      </span>
                    )}
                    {isCompleted && (
                      <span className="ml-auto text-xs text-green-600">Done</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <div className="sticky top-0 z-20 bg-white border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">Insights & Predictions</h1>
              <p className="text-xs text-muted-foreground">
                AI-powered retail analytics dashboard
              </p>
            </div>
            <Skeleton className="h-10 w-48 rounded-md" />
          </div>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-md" />
            ))}
          </div>
          <Skeleton className="h-10 w-full rounded-md" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Skeleton className="h-72 rounded-md lg:col-span-2" />
            <Skeleton className="h-72 rounded-md" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Skeleton className="h-32 rounded-md" />
            <Skeleton className="h-32 rounded-md" />
            <Skeleton className="h-32 rounded-md" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="sticky top-0 z-20 bg-white border-b px-6 py-4">
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
      <div className="sticky top-0 z-20 bg-white border-b px-6 py-4">
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
          <TabsTrigger value="analytics" className="flex-1">
            <BarChart3 className="size-4 mr-1.5" />
            Analytics
          </TabsTrigger>
          <TabsTrigger value="comparison" className="flex-1">
            <GitCompareArrows className="size-4 mr-1.5" />
            Follow-Up
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

        <TabsContent value="analytics">
          <Tabs defaultValue="overview">
            <TabsList className="w-full">
              <TabsTrigger value="overview" className="flex-1">
                <LayoutDashboard className="size-4 mr-1.5" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="revenue" className="flex-1">
                <DollarSign className="size-4 mr-1.5" />
                Revenue
              </TabsTrigger>
              <TabsTrigger value="stock" className="flex-1">
                <Package className="size-4 mr-1.5" />
                Stock
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
              <TabsTrigger value="funnel" className="flex-1">
                <MousePointerClick className="size-4 mr-1.5" />
                Funnel
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
                actionPlan={actionPlan}
                funnelSnapshot={funnelSnapshot}
                runId={selectedRunId}
              />
            </TabsContent>

            <TabsContent value="revenue">
              <RevenueSalesTab
                cards={cards}
                revenueSeries={revenueSeries}
                channelRevenueData={channelRevenueData}
                forecastSnapshot={forecastSnapshot}
                chartNarrative={chartNarratives?.narratives?.revenue_trend}
                snapshot={snapshot}
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
                snapshot={snapshot}
                forecastSnapshot={forecastSnapshot}
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
                snapshot={snapshot}
                campaignData={campaignPerformance}
              />
            </TabsContent>

            <TabsContent value="funnel">
              <FunnelSessionsTab
                cards={cards}
                funnelSnapshot={funnelSnapshot}
                sessionsAnalytics={sessionsAnalytics}
              />
            </TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="comparison">
          <RunComparisonTab
            comparison={runComparison}
            comparisonLoading={comparisonLoading}
            comparisonAi={comparisonAi}
            comparisonAiLoading={comparisonAiLoading}
            actionPlan={actionPlan}
            runs={runs}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
            compareWithRunId={compareWithRunId}
            onCompareWithChange={(id) => {
              setCompareWithRunId(id);
              setCompareEnabled(false);
            }}
            compareEnabled={compareEnabled}
            onCompare={() => setCompareEnabled(true)}
          />
        </TabsContent>

      </Tabs>
      </div>
    </div>
  );
}
