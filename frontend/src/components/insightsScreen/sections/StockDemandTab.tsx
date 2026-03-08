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
  ChevronDown,
  ChevronUp,
  ArrowRightLeft,
  MapPin,
  Truck,
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
import type { KpiCardRow, DemandForecastSku, ChartNarrativeData, LocationSummary, StoreTransfer } from "../dashboard/types";
import { getCardValue, fmtPercent, safeNum } from "../dashboard/formatters";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";
import { ChartNarrative } from "../charts/ChartNarrative";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const COLLAPSED_ROW_COUNT = 5;

const STATUS_BADGE: Record<string, { color: string; label: string }> = {
  critical: { color: "red", label: "Critical" },
  warning: { color: "orange", label: "Warning" },
  healthy: { color: "green", label: "Healthy" },
  unknown: { color: "gray", label: "Unknown" },
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
/* Stockout display helper                                             */
/* ------------------------------------------------------------------ */

function StockoutDisplay({ days }: { days: number | null }) {
  if (days === null || days === undefined) {
    return <span className="text-xs text-muted-foreground">No forecast</span>;
  }
  if (days >= 9999) {
    return <span className="text-xs text-green-600 font-medium">90+ days</span>;
  }

  let colorClass = "text-green-600";
  if (days < 7) colorClass = "text-red-600 font-semibold";
  else if (days < 14) colorClass = "text-orange-500 font-medium";

  return <span className={`text-sm tabular-nums ${colorClass}`}>{days}d</span>;
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
  chartNarrative?: ChartNarrativeData | null;
  locationSummary?: LocationSummary[];
  storeTransfers?: StoreTransfer[];
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function StockDemandTab({ cards, demandSkus, chartNarrative, locationSummary = [], storeTransfers = [] }: StockDemandTabProps) {
  /* ---------- Sort state ---------- */
  const [sortColumn, setSortColumn] = useState<SortColumn>("days_until_stockout");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [showAllRows, setShowAllRows] = useState(false);

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

  /* ---------- Visible rows (collapse/expand) ---------- */
  const visibleSkus = showAllRows ? sortedSkus : sortedSkus.slice(0, COLLAPSED_ROW_COUNT);
  const hasMoreRows = sortedSkus.length > COLLAPSED_ROW_COUNT;

  /* ---------- Health chart data: per-category breakdown ---------- */
  const healthData = useMemo(() => {
    const categoryMap: Record<string, { critical: number; warning: number; healthy: number }> = {};
    demandSkus.forEach((s) => {
      const cat = s.category ?? "Other";
      if (!categoryMap[cat]) categoryMap[cat] = { critical: 0, warning: 0, healthy: 0 };
      if (s.status === "critical") categoryMap[cat].critical++;
      else if (s.status === "warning") categoryMap[cat].warning++;
      else categoryMap[cat].healthy++;
    });
    return Object.entries(categoryMap)
      .map(([name, counts]) => ({ name, ...counts }))
      .sort((a, b) => (b.critical + b.warning) - (a.critical + a.warning));
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
      {/* Chart Narrative */}
      {chartNarrative && (
        <ChartNarrative narrative={chartNarrative.narrative} actionHint={chartNarrative.action_hint} />
      )}

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
          Row 2: Stock Recommendation Table (collapsed by default)
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
            <>
              <div className="overflow-x-auto">
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
                    {visibleSkus.map((sku) => {
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
                            <StockoutDisplay days={sku.days_until_stockout} />
                          </TableCell>
                          <TableCell>
                            <Badge color={statusInfo.color}>
                              {statusInfo.label}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              {/* Expand / Collapse toggle */}
              {hasMoreRows && (
                <div className="mt-3 text-center">
                  <button
                    type="button"
                    onClick={() => setShowAllRows((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                  >
                    {showAllRows ? (
                      <>
                        <ChevronUp className="size-3.5" />
                        Show less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="size-3.5" />
                        Show all {sortedSkus.length} items
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* ============================================================
          Row 3: Health by Status (per category) + Top Demand SKUs
          ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Inventory Health by Status — per category */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Inventory Health by Category
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartEnlargeWrapper title="Inventory Health by Category">
              <ChartContainer config={healthChartConfig} className="w-full" style={{ height: Math.max(220, healthData.length * 40) }}>
                <BarChart
                  data={healthData}
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
                    width={100}
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
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ChartContainer>
              {/* Legend */}
              <div className="flex flex-wrap gap-3 mt-3 justify-center">
                {([
                  { label: "Critical", color: "var(--chart-1)" },
                  { label: "Warning", color: "var(--chart-2)" },
                  { label: "Healthy", color: "var(--chart-4)" },
                ]).map((item) => (
                  <div key={item.label} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="rounded-sm shrink-0"
                      style={{
                        backgroundColor: item.color,
                        display: "inline-block",
                        width: 12,
                        height: 12,
                        minWidth: 12,
                        minHeight: 12,
                      }}
                    />
                    <span className="text-muted-foreground">{item.label}</span>
                  </div>
                ))}
              </div>
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

      {/* ============================================================
          Row 4: Stock by Location
          ============================================================ */}
      {locationSummary.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <MapPin className="size-4 text-blue-600" />
              <CardTitle className="text-base">Stock by Warehouse Location</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {locationSummary.map((loc) => (
                <div
                  key={loc.location}
                  className="rounded-lg border p-3 space-y-1"
                >
                  <div className="flex items-center gap-1.5">
                    <MapPin className="size-3 text-muted-foreground" />
                    <span className="text-sm font-semibold">{loc.location}</span>
                  </div>
                  <div className="text-lg font-bold tabular-nums">
                    {loc.total_stock.toLocaleString()}
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{loc.total_skus} SKUs</span>
                    <span>Avg: {Math.round(loc.avg_stock)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================================
          Row 5: Store Transfer Recommendations
          ============================================================ */}
      {storeTransfers.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="size-4 text-orange-600" />
              <CardTitle className="text-base">
                Store Transfer Recommendations
              </CardTitle>
            </div>
            <p className="text-sm text-muted-foreground">
              {storeTransfers.length} product{storeTransfers.length > 1 ? "s" : ""} could benefit from stock redistribution between warehouses
            </p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead className="text-right">Transfer Qty</TableHead>
                    <TableHead className="text-right">Days Left (To)</TableHead>
                    <TableHead>Urgency</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {storeTransfers.slice(0, 10).map((t, i) => (
                    <TableRow key={`${t.sku}-${t.to_location}-${i}`} className={t.urgency === "critical" ? "bg-red-50/50" : ""}>
                      <TableCell className="font-medium">
                        {t.product_name}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="size-3 text-green-600" />
                          <span className="text-sm">{t.from_location}</span>
                          <span className="text-xs text-muted-foreground">({t.from_stock})</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="size-3 text-red-500" />
                          <span className="text-sm">{t.to_location}</span>
                          <span className="text-xs text-muted-foreground">({t.to_stock})</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">
                        {t.transfer_qty.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`font-medium tabular-nums ${t.to_days_left < 7 ? "text-red-600" : "text-orange-500"}`}>
                          {t.to_days_left}d
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge color={t.urgency === "critical" ? "red" : "orange"}>
                          {t.urgency === "critical" ? "Critical" : "Warning"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================================
          Row 6: Supplier Performance
          ============================================================ */}
      {(() => {
        const supplierStockouts = getCardValue(cards, "supplier_stockouts", {}) as Record<string, number>;
        const supplierReliability = getCardValue(cards, "supplier_reliability", {}) as Record<string, number>;
        const supplierNames = Array.from(
          new Set([...Object.keys(supplierStockouts), ...Object.keys(supplierReliability)]),
        );
        if (supplierNames.length === 0) return null;

        return (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Truck className="size-4 text-indigo-600" />
                <CardTitle className="text-base">Supplier Performance</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {supplierNames.map((name) => {
                  const stockouts = supplierStockouts[name] ?? 0;
                  const reliability = supplierReliability[name] ?? 0;
                  const reliabilityPct = Math.round(reliability * 100);
                  const color =
                    reliabilityPct < 70
                      ? "red"
                      : reliabilityPct < 85
                        ? "orange"
                        : "green";
                  const colorClasses =
                    color === "red"
                      ? "border-red-200 bg-red-50/40"
                      : color === "orange"
                        ? "border-orange-200 bg-orange-50/40"
                        : "border-green-200 bg-green-50/40";
                  const textColor =
                    color === "red"
                      ? "text-red-600"
                      : color === "orange"
                        ? "text-orange-600"
                        : "text-green-600";

                  return (
                    <div
                      key={name}
                      className={`rounded-lg border p-4 space-y-2 ${colorClasses}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold">{name}</span>
                        <Badge color={color}>
                          {reliabilityPct}%
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Stockout incidents: <span className="font-medium text-foreground">{stockouts}</span>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Reliability</span>
                          <span className={`font-medium ${textColor}`}>{reliabilityPct}%</span>
                        </div>
                        <Progress value={reliabilityPct} className="h-1.5" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        );
      })()}
    </div>
  );
}
