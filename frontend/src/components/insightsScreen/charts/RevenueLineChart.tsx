import React from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
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
  // Find the boundary date where actuals end and forecast begins
  const forecastBoundary = React.useMemo(() => {
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i].revenue_actual != null && data[i].revenue_forecast != null) {
        return data[i].date;
      }
    }
    // Fallback: last date with actual data
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i].revenue_actual != null) return data[i].date;
    }
    return null;
  }, [data]);

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

        {/* Forecast boundary marker */}
        {forecastBoundary && (
          <ReferenceLine
            x={forecastBoundary}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{ value: "Forecast", position: "top", fontSize: 11, fill: "#94a3b8" }}
          />
        )}

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
