import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";

import {
  fmtCurrency2,
  fmtPercent,
  safeNum,
  getCardValue,
} from "../dashboard/formatters";
import type {
  KpiCardRow,
  FunnelSnapshot,
  SessionsAnalytics,
} from "../dashboard/types";

import {
  ArrowDown,
  Monitor,
  Smartphone,
  Tablet,
  MousePointerClick,
  ShoppingCart,
  CreditCard,
  Eye,
  Globe,
  Timer,
  TrendingDown,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Colors                                                              */
/* ------------------------------------------------------------------ */

const FUNNEL_COLORS = [
  "#3b82f6", // blue – sessions
  "#8b5cf6", // violet – product views
  "#f59e0b", // amber – add to cart
  "#f97316", // orange – begin checkout
  "#10b981", // emerald – purchases
];

const DEVICE_COLORS: Record<string, string> = {
  desktop: "#3b82f6",
  mobile: "#10b981",
  tablet: "#f59e0b",
};

const SOURCE_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "#6366f1",
  "#ec4899",
  "#14b8a6",
];

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface FunnelSessionsTabProps {
  cards: KpiCardRow[];
  funnelSnapshot: FunnelSnapshot | null;
  sessionsAnalytics: SessionsAnalytics | null;
}

/* ------------------------------------------------------------------ */
/* Chart configs                                                       */
/* ------------------------------------------------------------------ */

const funnelTrendConfig: ChartConfig = {
  conversion_rate: { label: "Conversion Rate", color: "#10b981" },
  cart_abandonment_rate: { label: "Cart Abandonment", color: "#ef4444" },
};

const sourceChartConfig: ChartConfig = {
  sessions: { label: "Sessions", color: "var(--chart-1)" },
};

/* ------------------------------------------------------------------ */
/* MiniKpi                                                             */
/* ------------------------------------------------------------------ */

interface MiniKpiProps {
  icon: React.ElementType;
  label: string;
  value: string;
  subtitle: string;
  iconColor: string;
  iconBg: string;
}

function MiniKpi({ icon: Icon, label, value, subtitle, iconColor, iconBg }: MiniKpiProps) {
  return (
    <Card className="gap-0">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-muted-foreground">{label}</span>
          <div className={`rounded-md p-1.5 ${iconBg}`}>
            <Icon className={`size-4 ${iconColor}`} />
          </div>
        </div>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Funnel Stage Bar                                                    */
/* ------------------------------------------------------------------ */

function FunnelStageBar({
  stages,
}: {
  stages: Array<{ name: string; value: number; color: string; dropOff?: string }>;
}) {
  const maxVal = Math.max(...stages.map((s) => s.value), 1);

  return (
    <div className="space-y-3">
      {stages.map((stage, i) => (
        <div key={stage.name} className="flex items-center gap-3">
          <div className="w-32 text-sm font-medium text-right shrink-0">
            {stage.name}
          </div>
          <div className="flex-1 relative">
            <div
              className="h-10 rounded-md flex items-center px-3 text-white text-sm font-semibold transition-all"
              style={{
                width: `${Math.max((stage.value / maxVal) * 100, 8)}%`,
                backgroundColor: stage.color,
              }}
            >
              {stage.value.toLocaleString()}
            </div>
          </div>
          {stage.dropOff && (
            <div className="w-20 text-xs text-red-500 font-medium flex items-center gap-1 shrink-0">
              <ArrowDown className="size-3" />
              {stage.dropOff}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function FunnelSessionsTab({
  cards,
  funnelSnapshot,
  sessionsAnalytics,
}: FunnelSessionsTabProps) {
  // KPI values from cards
  const conversionRate = getCardValue(cards, "conversion_rate", 0);
  const cartAbandonment = getCardValue(cards, "cart_abandonment_rate", 0);
  const avgSessionDuration = getCardValue(cards, "avg_session_duration", 0);
  const revenuePerSession = getCardValue(cards, "revenue_per_session", 0);
  const mobileConv = getCardValue(cards, "mobile_conversion_rate", 0);
  const desktopConv = getCardValue(cards, "desktop_conversion_rate", 0);
  const bounceRate = getCardValue(cards, "bounce_rate", 0);

  // Funnel stages from funnel_kpis
  const funnelKpis = funnelSnapshot?.funnel_kpis ?? {};
  const totalSessions = safeNum(funnelKpis.total_sessions);
  const totalProductViews = safeNum(funnelKpis.total_product_views);
  const totalAddToCart = safeNum(funnelKpis.total_add_to_cart);
  const totalCheckout = safeNum(funnelKpis.total_begin_checkout);
  const totalPurchases = safeNum(funnelKpis.total_purchases);

  const funnelStages = useMemo(() => {
    const stages = [
      { name: "Sessions", value: totalSessions, color: FUNNEL_COLORS[0] },
      { name: "Product Views", value: totalProductViews, color: FUNNEL_COLORS[1] },
      { name: "Add to Cart", value: totalAddToCart, color: FUNNEL_COLORS[2] },
      { name: "Checkout", value: totalCheckout, color: FUNNEL_COLORS[3] },
      { name: "Purchase", value: totalPurchases, color: FUNNEL_COLORS[4] },
    ];

    // Calculate drop-off percentages
    return stages.map((stage, i) => {
      if (i === 0) return { ...stage, dropOff: undefined };
      const prev = stages[i - 1].value;
      if (prev === 0) return { ...stage, dropOff: undefined };
      const dropPct = ((prev - stage.value) / prev) * 100;
      return { ...stage, dropOff: `-${dropPct.toFixed(1)}%` };
    });
  }, [totalSessions, totalProductViews, totalAddToCart, totalCheckout, totalPurchases]);

  // Daily funnel trends
  const dailyTrends = funnelSnapshot?.daily_trends ?? [];

  // Device breakdown
  const deviceData = useMemo(() => {
    if (!sessionsAnalytics) return [];
    const byDevice = sessionsAnalytics.by_device ?? {};
    const convByDevice = sessionsAnalytics.conversion_by_device ?? {};
    const revByDevice = sessionsAnalytics.avg_revenue_by_device ?? {};
    return Object.entries(byDevice)
      .map(([device, sessions]) => ({
        device,
        sessions: safeNum(sessions),
        conversion: safeNum(convByDevice[device]),
        avgRevenue: safeNum(revByDevice[device]),
      }))
      .sort((a, b) => b.sessions - a.sessions);
  }, [sessionsAnalytics]);

  // Traffic source breakdown
  const sourceData = useMemo(() => {
    if (!sessionsAnalytics) return [];
    const bySource = sessionsAnalytics.by_traffic_source ?? {};
    const convBySource = sessionsAnalytics.conversion_by_source ?? {};
    return Object.entries(bySource)
      .map(([source, sessions]) => ({
        source: source.replace(/_/g, " "),
        sessions: safeNum(sessions),
        conversion: safeNum(convBySource[source]),
      }))
      .sort((a, b) => b.sessions - a.sessions);
  }, [sessionsAnalytics]);

  // Landing page breakdown
  const landingData = useMemo(() => {
    if (!sessionsAnalytics) return [];
    const byLanding = sessionsAnalytics.by_landing_page ?? {};
    const convByLanding = sessionsAnalytics.conversion_by_landing ?? {};
    return Object.entries(byLanding)
      .map(([page, sessions]) => ({
        page,
        sessions: safeNum(sessions),
        conversion: safeNum(convByLanding[page]),
      }))
      .sort((a, b) => b.conversion - a.conversion);
  }, [sessionsAnalytics]);

  // Session duration distribution
  const durationData = useMemo(() => {
    if (!sessionsAnalytics) return [];
    const dist = sessionsAnalytics.session_duration_distribution ?? {};
    const convDist = sessionsAnalytics.session_duration_conversion ?? {};
    return Object.entries(dist).map(([bucket, count]) => ({
      bucket,
      sessions: safeNum(count),
      conversion: safeNum(convDist[bucket]),
    }));
  }, [sessionsAnalytics]);

  const noFunnelData = totalSessions === 0 && dailyTrends.length === 0;

  return (
    <div className="space-y-6">
      {/* Row 1: KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <MiniKpi
          icon={MousePointerClick}
          label="Conversion Rate"
          value={fmtPercent(conversionRate)}
          subtitle="Sessions → Purchase"
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50"
        />
        <MiniKpi
          icon={ShoppingCart}
          label="Cart Abandonment"
          value={fmtPercent(cartAbandonment)}
          subtitle="Added but didn't buy"
          iconColor="text-red-600"
          iconBg="bg-red-50"
        />
        <MiniKpi
          icon={Timer}
          label="Avg Session"
          value={`${Math.round(avgSessionDuration)}s`}
          subtitle="Session duration"
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={CreditCard}
          label="Rev / Session"
          value={fmtCurrency2(revenuePerSession)}
          subtitle="Revenue per session"
          iconColor="text-violet-600"
          iconBg="bg-violet-50"
        />
        <MiniKpi
          icon={Monitor}
          label="Desktop Conv"
          value={fmtPercent(desktopConv)}
          subtitle="Desktop conversion"
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={Smartphone}
          label="Mobile Conv"
          value={fmtPercent(mobileConv)}
          subtitle="Mobile conversion"
          iconColor="text-green-600"
          iconBg="bg-green-50"
        />
        <MiniKpi
          icon={TrendingDown}
          label="Bounce Rate"
          value={fmtPercent(bounceRate)}
          subtitle="Single-page sessions"
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
        />
      </div>

      {/* Row 2: Conversion Funnel */}
      <Card>
        <CardHeader>
          <CardTitle>Conversion Funnel</CardTitle>
          <CardDescription>
            Drop-off at each stage from session start to purchase
          </CardDescription>
        </CardHeader>
        <CardContent>
          {noFunnelData ? (
            <p className="text-sm text-muted-foreground py-12 text-center">
              No funnel data available. Run the pipeline to generate funnel analytics.
            </p>
          ) : (
            <FunnelStageBar stages={funnelStages} />
          )}
        </CardContent>
      </Card>

      {/* Row 3: Device Performance + Traffic Source */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Device Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Performance by Device</CardTitle>
            <CardDescription>Sessions, conversion & revenue by device type</CardDescription>
          </CardHeader>
          <CardContent>
            {deviceData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No device data available
              </p>
            ) : (
              <div className="space-y-0">
                {deviceData.map((d, i, arr) => {
                  const DeviceIcon =
                    d.device === "mobile" ? Smartphone :
                    d.device === "tablet" ? Tablet : Monitor;
                  const color = DEVICE_COLORS[d.device] ?? "#6b7280";
                  return (
                    <div
                      key={d.device}
                      className={`flex items-center gap-4 py-3 ${i < arr.length - 1 ? "border-b" : ""}`}
                    >
                      <div
                        className="rounded-md p-2"
                        style={{ backgroundColor: `${color}15` }}
                      >
                        <DeviceIcon className="size-5" style={{ color }} />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-semibold capitalize">{d.device}</div>
                        <div className="text-xs text-muted-foreground">
                          {d.sessions.toLocaleString()} sessions
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold">
                          {fmtPercent(d.conversion)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {fmtCurrency2(d.avgRevenue)} / session
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Traffic Source */}
        <Card>
          <CardHeader>
            <CardTitle>Traffic Sources</CardTitle>
            <CardDescription>Sessions & conversion by traffic source</CardDescription>
          </CardHeader>
          <CardContent>
            {sourceData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No traffic source data available
              </p>
            ) : (
              <ChartEnlargeWrapper title="Traffic Sources">
                <ChartContainer
                  config={sourceChartConfig}
                  className="w-full"
                  style={{ height: 280 }}
                >
                  <BarChart
                    data={sourceData}
                    margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="source"
                      tick={{ fontSize: 11 }}
                      angle={-25}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value, name) =>
                            name === "conversion"
                              ? fmtPercent(safeNum(value))
                              : safeNum(value).toLocaleString()
                          }
                        />
                      }
                    />
                    <Bar dataKey="sessions" radius={[4, 4, 0, 0]}>
                      {sourceData.map((_, idx) => (
                        <Cell
                          key={idx}
                          fill={SOURCE_COLORS[idx % SOURCE_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 4: Landing Page Effectiveness + Session Duration */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Landing Page Effectiveness */}
        <Card>
          <CardHeader>
            <CardTitle>Landing Page Effectiveness</CardTitle>
            <CardDescription>Conversion rate by landing page type</CardDescription>
          </CardHeader>
          <CardContent>
            {landingData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No landing page data available
              </p>
            ) : (
              <ChartEnlargeWrapper title="Landing Page Effectiveness">
                <ChartContainer
                  config={{ conversion: { label: "Conversion Rate", color: "#10b981" } }}
                  className="w-full"
                  style={{ height: 280 }}
                >
                  <BarChart
                    data={landingData}
                    margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="page"
                      tick={{ fontSize: 11 }}
                      angle={-25}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value) => fmtPercent(safeNum(value))}
                        />
                      }
                    />
                    <Bar dataKey="conversion" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>

        {/* Session Duration Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Session Duration Distribution</CardTitle>
            <CardDescription>Session count by duration with conversion overlay</CardDescription>
          </CardHeader>
          <CardContent>
            {durationData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No session duration data available
              </p>
            ) : (
              <ChartEnlargeWrapper title="Session Duration Distribution">
                <ChartContainer
                  config={{
                    sessions: { label: "Sessions", color: "#3b82f6" },
                    conversion: { label: "Conversion Rate", color: "#10b981" },
                  }}
                  className="w-full"
                  style={{ height: 280 }}
                >
                  <BarChart
                    data={durationData}
                    margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="left" />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value, name) =>
                            name === "conversion"
                              ? fmtPercent(safeNum(value))
                              : safeNum(value).toLocaleString()
                          }
                        />
                      }
                    />
                    <Bar yAxisId="left" dataKey="sessions" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="right" dataKey="conversion" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 5: Daily Funnel Trends */}
      {dailyTrends.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Daily Funnel Trends</CardTitle>
            <CardDescription>
              Conversion rate and cart abandonment over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartEnlargeWrapper title="Daily Funnel Trends">
              <ChartContainer
                config={funnelTrendConfig}
                className="w-full"
                style={{ height: 350 }}
              >
                <LineChart
                  data={dailyTrends}
                  margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => fmtPercent(safeNum(value))}
                      />
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="conversion_rate"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    name="Conversion Rate"
                  />
                  <Line
                    type="monotone"
                    dataKey="cart_abandonment_rate"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                    name="Cart Abandonment"
                  />
                </LineChart>
              </ChartContainer>
            </ChartEnlargeWrapper>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
