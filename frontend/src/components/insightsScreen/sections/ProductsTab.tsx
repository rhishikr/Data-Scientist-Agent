import React, { useMemo, useState } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../ui/table";
import { Badge } from "../../ui/badge";
import { Progress } from "../../ui/progress";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";
import { ChartEnlargeWrapper } from "../charts/ChartEnlargeWrapper";

import {
  fmtCurrency,
  fmtPercent,
  safeNum,
  getCardValue,
} from "../dashboard/formatters";
import type { KpiCardRow, Snapshot, DemandForecastSku } from "../dashboard/types";

import {
  Percent,
  RotateCcw,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  TableIcon,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const COLLAPSED_ROW_COUNT = 5;

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface ProductsTabProps {
  cards: KpiCardRow[];
  snapshot: Snapshot | null;
  demandSkus?: DemandForecastSku[];
}

/* ------------------------------------------------------------------ */
/* Chart configs                                                       */
/* ------------------------------------------------------------------ */

const topProductsChartConfig: ChartConfig = {
  revenue: { label: "Revenue", color: "var(--chart-2)" },
};

const bottomProductsChartConfig: ChartConfig = {
  revenue: { label: "Revenue", color: "var(--chart-1)" },
};

/* ------------------------------------------------------------------ */
/* View toggle                                                         */
/* ------------------------------------------------------------------ */

function ViewToggle({ view, onToggle }: { view: "table" | "chart"; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium bg-muted text-muted-foreground hover:bg-muted/80 transition-colors cursor-pointer"
    >
      {view === "table" ? (
        <>
          <BarChart3 className="size-3" />
          Chart
        </>
      ) : (
        <>
          <TableIcon className="size-3" />
          Table
        </>
      )}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function ProductsTab({ cards, snapshot, demandSkus = [] }: ProductsTabProps) {
  const [topView, setTopView] = useState<"table" | "chart">("table");
  const [bottomView, setBottomView] = useState<"table" | "chart">("table");
  const [showAllDiscount, setShowAllDiscount] = useState(false);
  const [showAllStockout, setShowAllStockout] = useState(false);

  // KPI values
  const avgMarginPct = getCardValue(cards, "avg_margin_pct", 0);
  const returnRate = getCardValue(cards, "return_rate_proxy", 0);
  const stockOutRisk = getCardValue(cards, "stock_out_risk_pct", 0);
  const inventoryTurnover = getCardValue(cards, "inventory_turnover_proxy", 0);

  // Table data
  const topProducts: Array<Record<string, any>> =
    snapshot?.tables?.top_products ?? [];
  const lowProducts: Array<Record<string, any>> =
    snapshot?.tables?.low_products ?? [];
  const discountWatchlist: Array<Record<string, any>> =
    snapshot?.tables?.discount_watchlist ?? [];

  // Revenue key helper
  const revenueKey = (row: Record<string, any>): number => {
    return safeNum(
      row.total_revenue ?? row.revenue ?? row.total_sales ?? row.value ?? 0,
      0,
    );
  };

  // Chart data
  const topChartData = topProducts.slice(0, 10).map((p) => ({
    name: String(p.name ?? p.product_name ?? p.sku ?? "Unknown").substring(0, 24),
    revenue: revenueKey(p),
  }));

  const bottomChartData = lowProducts.slice(0, 10).map((p) => ({
    name: String(p.name ?? p.product_name ?? p.sku ?? "Unknown").substring(0, 24),
    revenue: revenueKey(p),
  }));

  // Stockout risk products (critical + warning from demand forecast)
  const stockoutRiskProducts = useMemo(() => {
    return demandSkus
      .filter((s) => s.status === "critical" || s.status === "warning")
      .sort((a, b) => (a.days_until_stockout ?? 9999) - (b.days_until_stockout ?? 9999));
  }, [demandSkus]);

  const visibleStockout = showAllStockout
    ? stockoutRiskProducts
    : stockoutRiskProducts.slice(0, COLLAPSED_ROW_COUNT);

  // Discount watchlist: enriched with sorting
  const sortedDiscount = useMemo(() => {
    return [...discountWatchlist].sort((a, b) => {
      const dA = safeNum(a.discount_pct ?? a.discount ?? a.discount_percent ?? 0);
      const dB = safeNum(b.discount_pct ?? b.discount ?? b.discount_percent ?? 0);
      return dB - dA;
    });
  }, [discountWatchlist]);

  const visibleDiscount = showAllDiscount
    ? sortedDiscount
    : sortedDiscount.slice(0, COLLAPSED_ROW_COUNT);

  // Dynamic chart height
  const topChartHeight = Math.max(250, topChartData.length * 36);
  const bottomChartHeight = Math.max(250, bottomChartData.length * 36);

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Row 1: KPI Cards                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Avg Margin %</CardTitle>
            <Percent className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtPercent(avgMarginPct)}</div>
            <p className="text-xs text-muted-foreground">Product margin average</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Return Rate</CardTitle>
            <RotateCcw className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtPercent(returnRate)}</div>
            <p className="text-xs text-muted-foreground">Proxy return rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Stock-Out Risk</CardTitle>
            <AlertTriangle className="size-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmtPercent(stockOutRisk, 0)}</div>
            <p className="text-xs text-muted-foreground">SKUs below reorder threshold</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Inventory Turnover</CardTitle>
            <RefreshCw className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{safeNum(inventoryTurnover).toFixed(1)}x</div>
            <p className="text-xs text-muted-foreground">Based on sales / avg stock</p>
          </CardContent>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 2: Top & Bottom Products (Table default, with chart toggle)     */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top 10 Products */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Top 10 Products</CardTitle>
                <CardDescription>By revenue</CardDescription>
              </div>
              <ViewToggle
                view={topView}
                onToggle={() => setTopView((v) => (v === "table" ? "chart" : "table"))}
              />
            </div>
          </CardHeader>
          <CardContent>
            {topProducts.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No top products data available
              </p>
            ) : topView === "table" ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8">#</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {topProducts.slice(0, 10).map((p, i) => (
                      <TableRow key={p.sku ?? p.product_id ?? i}>
                        <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                        <TableCell className="font-medium">
                          {p.name ?? p.product_name ?? p.sku ?? "Unknown"}
                        </TableCell>
                        <TableCell>
                          {p.category ? <Badge variant="outline">{p.category}</Badge> : "-"}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {fmtCurrency(revenueKey(p))}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <ChartEnlargeWrapper title="Top 10 Products">
                <ChartContainer config={topProductsChartConfig} className="w-full" style={{ height: topChartHeight }}>
                  <BarChart data={topChartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(v: number) => fmtCurrency(v)} />
                    <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12 }} />
                    <ChartTooltip content={<ChartTooltipContent formatter={(value) => fmtCurrency(safeNum(value))} />} />
                    <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                      {topChartData.map((_, idx) => (
                        <Cell key={idx} fill="var(--chart-2)" />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>

        {/* Bottom 10 Products */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Bottom 10 Products</CardTitle>
                <CardDescription>By revenue</CardDescription>
              </div>
              <ViewToggle
                view={bottomView}
                onToggle={() => setBottomView((v) => (v === "table" ? "chart" : "table"))}
              />
            </div>
          </CardHeader>
          <CardContent>
            {lowProducts.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No bottom products data available
              </p>
            ) : bottomView === "table" ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8">#</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lowProducts.slice(0, 10).map((p, i) => (
                      <TableRow key={p.sku ?? p.product_id ?? i}>
                        <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                        <TableCell className="font-medium">
                          {p.name ?? p.product_name ?? p.sku ?? "Unknown"}
                        </TableCell>
                        <TableCell>
                          {p.category ? <Badge variant="outline">{p.category}</Badge> : "-"}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {fmtCurrency(revenueKey(p))}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <ChartEnlargeWrapper title="Bottom 10 Products">
                <ChartContainer config={bottomProductsChartConfig} className="w-full" style={{ height: bottomChartHeight }}>
                  <BarChart data={bottomChartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(v: number) => fmtCurrency(v)} />
                    <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12 }} />
                    <ChartTooltip content={<ChartTooltipContent formatter={(value) => fmtCurrency(safeNum(value))} />} />
                    <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                      {bottomChartData.map((_, idx) => (
                        <Cell key={idx} fill="var(--chart-1)" />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </ChartEnlargeWrapper>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 3: Stockout Risk Products                                       */}
      {/* ------------------------------------------------------------------ */}
      {stockoutRiskProducts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Stockout Risk Products</CardTitle>
            <CardDescription>
              {stockoutRiskProducts.length} products at risk of running out of stock
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">Current Stock</TableHead>
                    <TableHead className="text-right">Demand (30d)</TableHead>
                    <TableHead className="text-right">Days Left</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleStockout.map((sku) => {
                    const isCritical = sku.status === "critical";
                    return (
                      <TableRow key={sku.sku} className={isCritical ? "bg-red-50/50" : ""}>
                        <TableCell className="font-medium">
                          {sku.name ?? sku.sku}
                        </TableCell>
                        <TableCell>
                          {sku.category ? <Badge variant="outline">{sku.category}</Badge> : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <span className="tabular-nums">{sku.current_stock.toLocaleString()}</span>
                            <Progress
                              value={sku.forecast_qty_30d > 0 ? Math.min(100, Math.round((sku.current_stock / sku.forecast_qty_30d) * 100)) : 100}
                              className={`h-1.5 w-12 ${isCritical ? "[&>[data-slot=progress-indicator]]:bg-red-500" : "[&>[data-slot=progress-indicator]]:bg-orange-400"}`}
                            />
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {sku.forecast_qty_30d.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={`font-medium tabular-nums ${isCritical ? "text-red-600" : "text-orange-500"}`}>
                            {sku.days_until_stockout !== null ? `${sku.days_until_stockout}d` : "N/A"}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge color={isCritical ? "red" : "orange"}>
                            {isCritical ? "Critical" : "Warning"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            {stockoutRiskProducts.length > COLLAPSED_ROW_COUNT && (
              <div className="mt-3 text-center">
                <button
                  type="button"
                  onClick={() => setShowAllStockout((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                >
                  {showAllStockout ? (
                    <><ChevronUp className="size-3.5" /> Show less</>
                  ) : (
                    <><ChevronDown className="size-3.5" /> Show all {stockoutRiskProducts.length} at-risk products</>
                  )}
                </button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Row 4: Discount Watchlist Table (improved)                          */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Discount Watchlist</CardTitle>
          <CardDescription>
            Products with notable discount levels — high discount with low performance highlighted
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sortedDiscount.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No discount watchlist data available
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Product</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Discount %</TableHead>
                      <TableHead className="text-right">Rating</TableHead>
                      <TableHead className="text-right">Price</TableHead>
                      <TableHead className="text-right">Units Sold</TableHead>
                      <TableHead className="text-right">Revenue</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleDiscount.map((item, idx) => {
                      const discount = safeNum(
                        item.discount_pct ?? item.discount ?? item.discount_percent ?? 0,
                      );
                      const rating = safeNum(item.rating ?? item.avg_rating ?? item.average_rating ?? 0);
                      const price = safeNum(
                        item.price ?? item.retail_price ?? item.unit_price ?? 0,
                      );
                      const unitsSold = safeNum(item.times_purchased ?? item.units_sold ?? item.quantity ?? 0);
                      const revenue = safeNum(item.total_revenue ?? item.revenue ?? 0);
                      const highDiscountLowPerf = (discount > 1 ? discount : discount * 100) > 20 && revenue < 500;

                      return (
                        <TableRow
                          key={item.sku ?? item.product_id ?? idx}
                          className={highDiscountLowPerf ? "bg-red-50/50" : ""}
                        >
                          <TableCell className="font-medium">
                            {item.name ?? item.product_name ?? item.sku ?? "-"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{item.category ?? "-"}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {discount > 1 ? `${discount.toFixed(1)}%` : fmtPercent(discount)}
                          </TableCell>
                          <TableCell className="text-right">
                            {rating > 0 ? rating.toFixed(1) : "-"}
                          </TableCell>
                          <TableCell className="text-right">
                            {fmtCurrency(price)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {unitsSold > 0 ? unitsSold.toLocaleString() : "-"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {revenue > 0 ? fmtCurrency(revenue) : "-"}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              {sortedDiscount.length > COLLAPSED_ROW_COUNT && (
                <div className="mt-3 text-center">
                  <button
                    type="button"
                    onClick={() => setShowAllDiscount((v) => !v)}
                    className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                  >
                    {showAllDiscount ? (
                      <><ChevronUp className="size-3.5" /> Show less</>
                    ) : (
                      <><ChevronDown className="size-3.5" /> Show all {sortedDiscount.length} products</>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
