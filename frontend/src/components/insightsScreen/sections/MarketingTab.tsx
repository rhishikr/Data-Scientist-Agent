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
  CheckCircle,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface MarketingTabProps {
  cards: KpiCardRow[];
  channelRevenueData: Array<{ channel: string; revenue: number }>;
  forecastSnapshot: ForecastSnapshot | null;
}

// ---------------------------------------------------------------------------
// Chart config
// ---------------------------------------------------------------------------
const channelChartConfig: ChartConfig = {
  revenue: {
    label: "Revenue",
    color: "var(--chart-2)",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
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

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Row 1: KPI Cards                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* CAC */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">CAC</CardTitle>
            <DollarSign className="size-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtCurrency2(cac)}</div>
            <p className="text-xs text-muted-foreground">
              Customer acquisition cost
            </p>
          </CardContent>
        </Card>

        {/* ROAS */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">ROAS</CardTitle>
            <TrendingUp className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{safeNum(roas).toFixed(1)}x</div>
            <p className="text-xs text-muted-foreground">
              Return on ad spend
            </p>
          </CardContent>
        </Card>

        {/* Campaign CR */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Campaign CR</CardTitle>
            <Target className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtPercent(campaignCr)}</div>
            <p className="text-xs text-muted-foreground">
              Campaign conversion rate
            </p>
          </CardContent>
        </Card>

        {/* Promo Uplift */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Promo Uplift</CardTitle>
            <Sparkles className="size-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtPercent(promoUplift, 2)}</div>
            <p className="text-xs text-muted-foreground">
              Promotion-driven uplift (proxy)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 2: Revenue by Channel Bar Chart                                 */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Revenue by Channel</CardTitle>
          <CardDescription>
            Marketing channel performance based on snapshot data
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sortedChannelData.length === 0 ? (
            <p className="text-sm text-muted-foreground py-12 text-center">
              No channel revenue data available
            </p>
          ) : (
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
                    <Cell key={idx} fill="var(--chart-2)" />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Row 3: Marketing Summary & Executive Recommendations                */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Marketing Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Megaphone className="size-5 text-teal-600" />
              <CardTitle>Marketing Summary</CardTitle>
            </div>
            <CardDescription>Key marketing performance stats</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-sm text-muted-foreground">
                  Total Channel Revenue
                </span>
                <span className="text-sm font-medium">
                  {fmtCurrency(totalChannelRevenue)}
                </span>
              </div>

              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-sm text-muted-foreground">
                  Top Channel
                </span>
                <span className="text-sm font-medium">
                  {topChannel
                    ? `${topChannel.channel} (${fmtCurrency(topChannel.revenue)})`
                    : "N/A"}
                </span>
              </div>

              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-sm text-muted-foreground">
                  Customer Acquisition Cost
                </span>
                <span className="text-sm font-medium">{fmtCurrency2(cac)}</span>
              </div>

              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-sm text-muted-foreground">
                  Return on Ad Spend
                </span>
                <span className="text-sm font-medium">
                  {safeNum(roas).toFixed(1)}x
                </span>
              </div>

              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-sm text-muted-foreground">
                  Campaign Conversion Rate
                </span>
                <span className="text-sm font-medium">
                  {fmtPercent(campaignCr)}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">
                  Promotion Uplift
                </span>
                <span className="text-sm font-medium">
                  {fmtPercent(promoUplift, 2)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Executive Recommendations */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Lightbulb className="size-5 text-amber-500" />
              <CardTitle>Executive Recommendations</CardTitle>
            </div>
            <CardDescription>
              Rule-based recommended actions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recommendedActions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No recommendations available
              </p>
            ) : (
              <ul className="space-y-3">
                {recommendedActions.map((action, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <CheckCircle className="size-4 mt-0.5 shrink-0 text-teal-600" />
                    <span className="text-sm leading-relaxed">{action}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
