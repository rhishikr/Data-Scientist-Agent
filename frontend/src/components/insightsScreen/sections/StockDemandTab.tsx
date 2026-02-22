import React, { useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import {
  AlertTriangle,
  ShieldAlert,
  Package,
  ArrowUpDown,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Progress } from "../../ui/progress";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "../../ui/table";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import type { KpiCardRow, DemandForecastSku } from "../dashboard/types";
import { getCardValue, fmtPercent, safeNum } from "../dashboard/formatters";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";

/* ------------------------------------------------------------------ */
/* Status badge helper                                                 */
/* ------------------------------------------------------------------ */

const STATUS_BADGE: Record<string, { className: string; label: string }> = {
  critical: { className: "bg-red-100 text-red-700", label: "Critical" },
  warning: { className: "bg-amber-100 text-amber-700", label: "Warning" },
  healthy: { className: "bg-green-100 text-green-700", label: "Healthy" },
  unknown: { className: "bg-gray-100 text-gray-700", label: "Unknown" },
};

/* ------------------------------------------------------------------ */
/* Chart configs                                                       */
/* ------------------------------------------------------------------ */

const healthChartConfig = {
  critical: { label: "Critical", color: "var(--chart-1)" },
  warning: { label: "Warning", color: "var(--chart-2)" },
  healthy: { label: "Healthy", color: "var(--chart-4)" },
} satisfies ChartConfig;

const demandChartConfig = {
  forecast_qty_30d: {
    label: "Forecast Qty (30d)",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

/* ------------------------------------------------------------------ */
/* Small KPI card component                                            */
/* ------------------------------------------------------------------ */

interface MiniKpiProps {
  icon: React.ElementType;
  label: string;
  value: string;
  iconColor: string;
  iconBg: string;
}

function MiniKpi({ icon: Icon, label, value, iconColor, iconBg }: MiniKpiProps) {
  return (
    <Card className="py-3 px-4 gap-0">
      <CardContent className="p-0">
        <div className="flex items-center gap-2 mb-2">
          <div className={`rounded-md p-1.5 ${iconBg}`}>
            <Icon className={`size-3.5 ${iconColor}`} />
          </div>
        </div>
        <div className="text-xl font-semibold tracking-tight leading-none mb-1">
          {value}
        </div>
        <p className="text-xs text-muted-foreground leading-tight">{label}</p>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Sort type                                                           */
/* ------------------------------------------------------------------ */

type SortColumn =
  | "sku"
  | "name"
  | "category"
  | "forecast_qty_30d"
  | "current_stock"
  | "days_until_stockout"
  | "status";
type SortDirection = "asc" | "desc";

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface StockDemandTabProps {
  cards: KpiCardRow[];
  demandSkus: DemandForecastSku[];
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function StockDemandTab({ cards, demandSkus }: StockDemandTabProps) {
  /* ---------- Sort state ---------- */
  const [sortColumn, setSortColumn] = useState<SortColumn>("days_until_stockout");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const handleSort = (col: SortColumn) => {
    if (sortColumn === col) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(col);
      setSortDirection("asc");
    }
  };

  /* ---------- KPI values ---------- */
  const stockOutRisk = getCardValue(cards, "stock_out_risk_pct");
  const inventoryTurnover = getCardValue(cards, "inventory_turnover_proxy");
  const criticalCount = useMemo(
    () => demandSkus.filter((s) => s.status === "critical").length,
    [demandSkus],
  );
  const warningCount = useMemo(
    () => demandSkus.filter((s) => s.status === "warning").length,
    [demandSkus],
  );

  /* ---------- Sorted SKUs ---------- */
  const sortedSkus = useMemo(() => {
    const STATUS_RANK: Record<string, number> = {
      critical: 0,
      warning: 1,
      healthy: 2,
      unknown: 3,
    };

    return [...demandSkus].sort((a, b) => {
      let cmp = 0;
      switch (sortColumn) {
        case "sku":
          cmp = a.sku.localeCompare(b.sku);
          break;
        case "name":
          cmp = (a.name ?? "").localeCompare(b.name ?? "");
          break;
        case "category":
          cmp = (a.category ?? "").localeCompare(b.category ?? "");
          break;
        case "forecast_qty_30d":
          cmp = a.forecast_qty_30d - b.forecast_qty_30d;
          break;
        case "current_stock":
          cmp = a.current_stock - b.current_stock;
          break;
        case "days_until_stockout":
          cmp = (a.days_until_stockout ?? 9999) - (b.days_until_stockout ?? 9999);
          break;
        case "status":
          cmp = (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9);
          break;
      }
      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [demandSkus, sortColumn, sortDirection]);

  /* ---------- Health chart data ---------- */
  const healthData = useMemo(() => {
    const counts: Record<string, number> = {
      critical: 0,
      warning: 0,
      healthy: 0,
    };
    demandSkus.forEach((s) => {
      if (s.status in counts) {
        counts[s.status]++;
      }
    });
    return [
      {
        name: "Inventory",
        critical: counts.critical,
        warning: counts.warning,
        healthy: counts.healthy,
      },
    ];
  }, [demandSkus]);

  /* ---------- Top demand SKUs ---------- */
  const topDemandSkus = useMemo(() => {
    return [...demandSkus]
      .sort((a, b) => b.forecast_qty_30d - a.forecast_qty_30d)
      .slice(0, 10)
      .map((s) => ({
        name: s.name ?? s.sku,
        forecast_qty_30d: s.forecast_qty_30d,
      }));
  }, [demandSkus]);

  /* ---------- Column header helper ---------- */
  function SortableHeader({
    column,
    label,
  }: {
    column: SortColumn;
    label: string;
  }) {
    return (
      <TableHead
        className="cursor-pointer select-none hover:bg-muted/50 transition-colors"
        onClick={() => handleSort(column)}
      >
        <div className="flex items-center gap-1">
          {label}
          <ArrowUpDown className="size-3 text-muted-foreground" />
          {sortColumn === column && (
            <span className="text-[10px]">
              {sortDirection === "asc" ? "\u25B2" : "\u25BC"}
            </span>
          )}
        </div>
      </TableHead>
    );
  }

  return (
    <div className="space-y-6">
      {/* ============================================================
          Row 1: 4 KPI cards
          ============================================================ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniKpi
          icon={AlertTriangle}
          label="Stock-Out Risk %"
          value={fmtPercent(stockOutRisk)}
          iconColor="text-red-600"
          iconBg="bg-red-50"
        />
        <MiniKpi
          icon={Package}
          label="Inventory Turnover"
          value={safeNum(inventoryTurnover).toFixed(1)}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />
        <MiniKpi
          icon={ShieldAlert}
          label="Critical Items"
          value={String(criticalCount)}
          iconColor="text-orange-600"
          iconBg="bg-orange-50"
        />
        <MiniKpi
          icon={AlertTriangle}
          label="Warning Items"
          value={String(warningCount)}
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
        />
      </div>

      {/* ============================================================
          Row 2: Stock Recommendation Table
          ============================================================ */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Stock Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {sortedSkus.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No demand forecast data available
            </p>
          ) : (
            <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <SortableHeader column="sku" label="SKU" />
                    <SortableHeader column="name" label="Product" />
                    <SortableHeader column="category" label="Category" />
                    <SortableHeader column="forecast_qty_30d" label="Predicted Demand (30d)" />
                    <SortableHeader column="current_stock" label="Current Stock" />
                    <SortableHeader column="days_until_stockout" label="Days Until Stockout" />
                    <SortableHeader column="status" label="Status" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedSkus.map((sku) => {
                    const statusInfo =
                      STATUS_BADGE[sku.status] ?? STATUS_BADGE.unknown;
                    const stockPct =
                      sku.forecast_qty_30d > 0
                        ? Math.min(
                            100,
                            Math.round(
                              (sku.current_stock / sku.forecast_qty_30d) * 100,
                            ),
                          )
                        : 100;

                    return (
                      <TableRow key={sku.sku}>
                        <TableCell className="font-mono text-xs">
                          {sku.sku}
                        </TableCell>
                        <TableCell>{sku.name ?? "-"}</TableCell>
                        <TableCell>{sku.category ?? "-"}</TableCell>
                        <TableCell className="text-right">
                          {sku.forecast_qty_30d.toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="text-sm tabular-nums w-14 text-right">
                              {sku.current_stock.toLocaleString()}
                            </span>
                            <Progress
                              value={stockPct}
                              className="h-1.5 w-16"
                            />
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {sku.days_until_stockout !== null
                            ? sku.days_until_stockout
                            : "N/A"}
                        </TableCell>
                        <TableCell>
                          <Badge className={statusInfo.className}>
                            {statusInfo.label}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ============================================================
          Row 3: Health by Status + Top Demand SKUs
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Inventory Health by Status (stacked bar) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Inventory Health by Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartEnlargeWrapper title="Inventory Health by Status">
              <ChartContainer config={healthChartConfig} className="w-full" style={{ height: 220 }}>
                <BarChart
                  data={healthData}
                  margin={{ top: 8, right: 12, bottom: 0, left: 12 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="critical"
                    stackId="status"
                    fill="var(--chart-1)"
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="warning"
                    stackId="status"
                    fill="var(--chart-2)"
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="healthy"
                    stackId="status"
                    fill="var(--chart-4)"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            </ChartEnlargeWrapper>
          </CardContent>
        </Card>

        {/* Top Demand SKUs (horizontal bar) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Demand SKUs</CardTitle>
          </CardHeader>
          <CardContent>
            {topDemandSkus.length === 0 ? (
              <div className="flex items-center justify-center h-[220px] text-sm text-muted-foreground">
                No demand data
              </div>
            ) : (
              <ChartEnlargeWrapper title="Top Demand SKUs">
                <ChartContainer config={demandChartConfig} className="w-full" style={{ height: 320 }}>
                  <BarChart
                    data={topDemandSkus}
                    layout="vertical"
                    margin={{ top: 8, right: 12, bottom: 0, left: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      width={120}
                    />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar
                      dataKey="forecast_qty_30d"
                      fill="var(--chart-1)"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
