import React from "react";
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
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "../../ui/chart";

import {
  fmtCurrency,
  fmtPercent,
  safeNum,
  getCardValue,
} from "../dashboard/formatters";
import type { KpiCardRow, Snapshot } from "../dashboard/types";

import {
  Percent,
  RotateCcw,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface ProductsTabProps {
  cards: KpiCardRow[];
  snapshot: Snapshot | null;
}

// ---------------------------------------------------------------------------
// Chart configs
// ---------------------------------------------------------------------------
const topProductsChartConfig: ChartConfig = {
  revenue: {
    label: "Revenue",
    color: "var(--chart-2)",
  },
};

const bottomProductsChartConfig: ChartConfig = {
  revenue: {
    label: "Revenue",
    color: "var(--chart-1)",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function ProductsTab({ cards, snapshot }: ProductsTabProps) {
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

  // Determine the numeric key for revenue in product rows
  const revenueKey = (row: Record<string, any>): number => {
    return safeNum(
      row.total_revenue ?? row.revenue ?? row.total_sales ?? row.value ?? 0,
      0,
    );
  };

  // Prepare chart data
  const topChartData = topProducts.slice(0, 10).map((p) => ({
    name: String(p.name ?? p.product_name ?? p.sku ?? "Unknown").substring(0, 24),
    revenue: revenueKey(p),
  }));

  const bottomChartData = lowProducts.slice(0, 10).map((p) => ({
    name: String(p.name ?? p.product_name ?? p.sku ?? "Unknown").substring(0, 24),
    revenue: revenueKey(p),
  }));

  // Dynamic chart height based on number of bars
  const topChartHeight = Math.max(250, topChartData.length * 36);
  const bottomChartHeight = Math.max(250, bottomChartData.length * 36);

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Row 1: KPI Cards                                                    */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Avg Margin % */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Avg Margin %</CardTitle>
            <Percent className="size-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {fmtPercent(avgMarginPct)}
            </div>
            <p className="text-xs text-muted-foreground">Product margin average</p>
          </CardContent>
        </Card>

        {/* Return Rate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Return Rate</CardTitle>
            <RotateCcw className="size-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {fmtPercent(returnRate)}
            </div>
            <p className="text-xs text-muted-foreground">Proxy return rate</p>
          </CardContent>
        </Card>

        {/* Stock-Out Risk */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Stock-Out Risk</CardTitle>
            <AlertTriangle className="size-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {fmtPercent(stockOutRisk, 0)}
            </div>
            <p className="text-xs text-muted-foreground">SKUs below reorder threshold</p>
          </CardContent>
        </Card>

        {/* Inventory Turnover */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm">Inventory Turnover</CardTitle>
            <RefreshCw className="size-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {safeNum(inventoryTurnover).toFixed(1)}x
            </div>
            <p className="text-xs text-muted-foreground">Based on sales / avg stock</p>
          </CardContent>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 2: Top & Bottom Products Charts                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top 10 Products */}
        <Card>
          <CardHeader>
            <CardTitle>Top 10 Products</CardTitle>
            <CardDescription>By revenue</CardDescription>
          </CardHeader>
          <CardContent>
            {topChartData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No top products data available
              </p>
            ) : (
              <ChartContainer
                config={topProductsChartConfig}
                className="w-full"
                style={{ height: topChartHeight }}
              >
                <BarChart
                  data={topChartData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(v: number) => fmtCurrency(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={140}
                    tick={{ fontSize: 12 }}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) =>
                          fmtCurrency(safeNum(value))
                        }
                      />
                    }
                  />
                  <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                    {topChartData.map((_, idx) => (
                      <Cell key={idx} fill="var(--chart-2)" />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        {/* Bottom 10 Products */}
        <Card>
          <CardHeader>
            <CardTitle>Bottom 10 Products</CardTitle>
            <CardDescription>By revenue</CardDescription>
          </CardHeader>
          <CardContent>
            {bottomChartData.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No bottom products data available
              </p>
            ) : (
              <ChartContainer
                config={bottomProductsChartConfig}
                className="w-full"
                style={{ height: bottomChartHeight }}
              >
                <BarChart
                  data={bottomChartData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(v: number) => fmtCurrency(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={140}
                    tick={{ fontSize: 12 }}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) =>
                          fmtCurrency(safeNum(value))
                        }
                      />
                    }
                  />
                  <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                    {bottomChartData.map((_, idx) => (
                      <Cell key={idx} fill="var(--chart-1)" />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Row 3: Discount Watchlist Table                                      */}
      {/* ------------------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <CardTitle>Discount Watchlist</CardTitle>
          <CardDescription>
            Products with notable discount levels to monitor
          </CardDescription>
        </CardHeader>
        <CardContent>
          {discountWatchlist.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No discount watchlist data available
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SKU</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Discount%</TableHead>
                  <TableHead className="text-right">Rating</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {discountWatchlist.map((item, idx) => {
                  const discount = safeNum(
                    item.discount_pct ?? item.discount ?? item.discount_percent ?? 0,
                  );
                  const rating = safeNum(item.rating ?? item.avg_rating ?? 0);
                  const price = safeNum(
                    item.price ?? item.retail_price ?? item.unit_price ?? 0,
                  );

                  return (
                    <TableRow key={item.sku ?? item.product_id ?? idx}>
                      <TableCell className="font-mono text-xs">
                        {item.sku ?? item.product_id ?? "-"}
                      </TableCell>
                      <TableCell>
                        {item.name ?? item.product_name ?? "-"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {item.category ?? "-"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {discount > 1
                          ? `${discount.toFixed(1)}%`
                          : fmtPercent(discount)}
                      </TableCell>
                      <TableCell className="text-right">
                        {rating.toFixed(1)}
                      </TableCell>
                      <TableCell className="text-right">
                        {fmtCurrency(price)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
