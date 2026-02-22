import React from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import type { RevenueForecastPoint } from "../dashboard/types";
import { fmtCurrency } from "../dashboard/formatters";
import { ChartEnlargeWrapper } from "./ChartEnlargeWrapper";

/* ------------------------------------------------------------------ */
/* Chart config                                                        */
/* ------------------------------------------------------------------ */

const chartConfig = {
  revenue_actual: {
    label: "Actual Revenue",
    color: "var(--chart-1)",
  },
  revenue_forecast: {
    label: "Forecast",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig;

/* ------------------------------------------------------------------ */
/* Date tick formatter  (e.g. "Jan 15")                                */
/* ------------------------------------------------------------------ */

function formatDateTick(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
  } catch {
    return dateStr;
  }
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

interface RevenueLineChartProps {
  data: RevenueForecastPoint[];
  height?: number;
}

export function RevenueLineChart({
  data,
  height = 350,
}: RevenueLineChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-muted-foreground"
        style={{ height }}
      >
        No revenue data available
      </div>
    );
  }

  return (
    <ChartEnlargeWrapper title="Revenue Trend">
    <ChartContainer config={chartConfig} className="w-full" style={{ height }}>
      <ComposedChart
        data={data}
        margin={{ top: 8, right: 12, bottom: 0, left: 12 }}
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} />

        <XAxis
          dataKey="date"
          tickFormatter={formatDateTick}
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />

        <YAxis
          tickFormatter={(v: number) => fmtCurrency(v)}
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />

        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatDateTick(String(label))}
              formatter={(value, name) => {
                const label =
                  name === "revenue_actual" ? "Actual" : "Forecast";
                return (
                  <span className="flex items-center justify-between gap-4">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-mono font-medium tabular-nums">
                      {fmtCurrency(Number(value))}
                    </span>
                  </span>
                );
              }}
            />
          }
        />

        {/* Actual revenue as a filled area */}
        <Area
          type="monotone"
          dataKey="revenue_actual"
          stroke="var(--color-revenue_actual)"
          fill="var(--color-revenue_actual)"
          fillOpacity={0.15}
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />

        {/* Forecast as a dashed line */}
        <Line
          type="monotone"
          dataKey="revenue_forecast"
          stroke="var(--color-revenue_forecast)"
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          connectNulls={false}
        />
      </ComposedChart>
    </ChartContainer>
    </ChartEnlargeWrapper>
  );
}
