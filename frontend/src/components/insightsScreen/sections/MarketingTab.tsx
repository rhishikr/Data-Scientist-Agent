import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
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
  fmtCurrency,
  fmtCurrency2,
  fmtPercent,
  safeNum,
  getCardValue,
} from "../dashboard/formatters";
import type { KpiCardRow, ForecastSnapshot } from "../dashboard/types";

import {
  DollarSign,
  TrendingUp,
  Target,
  Sparkles,
  Megaphone,
  Lightbulb,
  ArrowRight,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Channel colors (assigned per-bar for visual variety)                 */
/* ------------------------------------------------------------------ */

const CHANNEL_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "#6366f1", // indigo
  "#ec4899", // pink
  "#14b8a6", // teal
];

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface MarketingTabProps {
  cards: KpiCardRow[];
  channelRevenueData: Array<{ channel: string; revenue: number }>;
  forecastSnapshot: ForecastSnapshot | null;
}

/* ------------------------------------------------------------------ */
/* Chart config                                                        */
/* ------------------------------------------------------------------ */

const channelChartConfig: ChartConfig = {
  revenue: {
    label: "Revenue",
    color: "var(--chart-2)",
  },
};

/* ------------------------------------------------------------------ */
/* MiniKpi card (consistent with other tabs)                           */
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
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function MarketingTab({
  cards,
  channelRevenueData,
  forecastSnapshot,
}: MarketingTabProps) {
  // KPI values
  const cac = getCardValue(cards, "cac", 0);
  const roas = getCardValue(cards, "roas", 0);
  const campaignCr = getCardValue(cards, "campaign_cr", 0);
  const promoUplift = getCardValue(cards, "promo_uplift", 0);

  // Sort channel revenue data descending
  const sortedChannelData = useMemo(() => {
    return [...channelRevenueData].sort((a, b) => b.revenue - a.revenue);
  }, [channelRevenueData]);

  // Executive insights
  const recommendedActions =
    forecastSnapshot?.executive_insights?.recommended_actions_rule_based ?? [];

  // Marketing summary stats
  const totalChannelRevenue = useMemo(() => {
    return sortedChannelData.reduce((sum, d) => sum + safeNum(d.revenue), 0);
  }, [sortedChannelData]);

  const topChannel = useMemo(() => {
    if (sortedChannelData.length === 0) return null;
    return sortedChannelData[0];
  }, [sortedChannelData]);

  // Top channel share
  const topChannelShare = topChannel
    ? Math.round((topChannel.revenue / Math.max(totalChannelRevenue, 1)) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Row 1: KPI Cards (improved styling)                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniKpi
          icon={DollarSign}
          label="CAC"
          value={fmtCurrency2(cac)}
          subtitle="Customer acquisition cost"
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={TrendingUp}
          label="ROAS"
          value={`${safeNum(roas).toFixed(1)}x`}
          subtitle="Return on ad spend"
          iconColor="text-green-600"
          iconBg="bg-green-50"
        />
        <MiniKpi
          icon={Target}
          label="Campaign CR"
          value={fmtPercent(campaignCr)}
          subtitle="Campaign conversion rate"
          iconColor="text-teal-600"
          iconBg="bg-teal-50"
        />
        <MiniKpi
          icon={Sparkles}
          label="Promo Uplift"
          value={fmtPercent(promoUplift, 2)}
          subtitle="Promotion-driven uplift"
          iconColor="text-purple-600"
          iconBg="bg-purple-50"
        />
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 2: Revenue by Channel Bar Chart (color-coded bars)              */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Revenue by Channel</CardTitle>
          <CardDescription>
            Marketing channel performance — {sortedChannelData.length} channels tracked
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sortedChannelData.length === 0 ? (
            <p className="text-sm text-muted-foreground py-12 text-center">
              No channel revenue data available
            </p>
          ) : (
            <ChartEnlargeWrapper title="Revenue by Channel">
              <ChartContainer
                config={channelChartConfig}
                className="w-full"
                style={{ height: 350 }}
              >
                <BarChart
                  data={sortedChannelData}
                  margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="channel"
                    tick={{ fontSize: 12 }}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tickFormatter={(v: number) => fmtCurrency(v)} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => fmtCurrency(safeNum(value))}
                      />
                    }
                  />
                  <Bar dataKey="revenue" radius={[4, 4, 0, 0]}>
                    {sortedChannelData.map((_, idx) => (
                      <Cell key={idx} fill={CHANNEL_COLORS[idx % CHANNEL_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </ChartEnlargeWrapper>
          )}
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Row 3: Marketing Summary & Executive Recommendations                */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Marketing Summary (improved card styling) */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="rounded-md p-1.5 bg-teal-50">
                <Megaphone className="size-4 text-teal-600" />
              </div>
              <CardTitle>Marketing Summary</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-0">
            {([
              { label: "Total Channel Revenue", value: fmtCurrency(totalChannelRevenue) },
              {
                label: "Top Channel",
                value: topChannel
                  ? `${topChannel.channel} (${topChannelShare}% share)`
                  : "N/A",
              },
              { label: "Customer Acquisition Cost", value: fmtCurrency2(cac) },
              { label: "Return on Ad Spend", value: `${safeNum(roas).toFixed(1)}x` },
              { label: "Campaign Conversion Rate", value: fmtPercent(campaignCr) },
              { label: "Promotion Uplift", value: fmtPercent(promoUplift, 2) },
            ]).map((item, i, arr) => (
              <div
                key={item.label}
                className={`flex justify-between items-center py-2.5 ${i < arr.length - 1 ? "border-b" : ""}`}
              >
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <span className="text-sm font-semibold">{item.value}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Executive Recommendations (card-style list) */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="rounded-md p-1.5 bg-amber-50">
                <Lightbulb className="size-4 text-amber-600" />
              </div>
              <CardTitle>Recommendations</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {recommendedActions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No recommendations available
              </p>
            ) : (
              <div className="space-y-2.5">
                {recommendedActions.map((action, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 rounded-lg border bg-muted/30 p-3"
                  >
                    <div className="rounded-full bg-teal-100 p-1 mt-0.5">
                      <ArrowRight className="size-3 text-teal-700" />
                    </div>
                    <span className="text-sm leading-relaxed">{action}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
