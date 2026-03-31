import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Package, TrendingUp, AlertTriangle, DollarSign } from "lucide-react";
import { ChatAssistant } from "./ChatAssistant";

const forecastData = [
  { date: "Week 1", actual: 42300, forecast: 41800 },
  { date: "Week 2", actual: 38900, forecast: 39200 },
  { date: "Week 3", actual: 45200, forecast: 44800 },
  { date: "Week 4", actual: 41500, forecast: 42100 },
  { date: "Week 5", actual: null, forecast: 47300 },
  { date: "Week 6", actual: null, forecast: 49100 },
];

const stockOutData = [
  { category: "Electronics", risk: 8 },
  { category: "Apparel", risk: 5 },
  { category: "Home & Garden", risk: 3 },
  { category: "Sports", risk: 4 },
  { category: "Books", risk: 2 },
  { category: "Toys", risk: 1 },
];

const topSKUs = [
  {
    sku: "SKU-2847",
    name: "Wireless Headphones Pro",
    category: "Electronics",
    demand: 847,
    stock: 234,
    risk: "High",
    days: 3,
  },
  {
    sku: "SKU-1923",
    name: "Running Shoes Elite",
    category: "Sports",
    demand: 623,
    stock: 412,
    risk: "Medium",
    days: 8,
  },
  {
    sku: "SKU-5621",
    name: "Smart Watch Series 5",
    category: "Electronics",
    demand: 534,
    stock: 89,
    risk: "High",
    days: 2,
  },
  {
    sku: "SKU-8234",
    name: "Yoga Mat Premium",
    category: "Sports",
    demand: 412,
    stock: 567,
    risk: "Low",
    days: 16,
  },
  {
    sku: "SKU-4729",
    name: "Coffee Maker Deluxe",
    category: "Home & Garden",
    demand: 389,
    stock: 145,
    risk: "Medium",
    days: 5,
  },
  {
    sku: "SKU-9156",
    name: "Designer Sunglasses",
    category: "Apparel",
    demand: 356,
    stock: 78,
    risk: "High",
    days: 3,
  },
  {
    sku: "SKU-3482",
    name: "Bluetooth Speaker",
    category: "Electronics",
    demand: 298,
    stock: 423,
    risk: "Low",
    days: 18,
  },
  {
    sku: "SKU-7821",
    name: "Kitchen Knife Set",
    category: "Home & Garden",
    demand: 267,
    stock: 312,
    risk: "Low",
    days: 14,
  },
];

export function InventorySalesScreen() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
      {/* Main Content */}
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mb-2">Inventory & Sales</h1>
            <p className="text-muted-foreground">
              AI-powered sales forecasting and inventory optimization
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Select defaultValue="all">
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="electronics">Electronics</SelectItem>
                <SelectItem value="apparel">Apparel</SelectItem>
                <SelectItem value="home">Home & Garden</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Forecasted Revenue</CardTitle>
              <DollarSign className="size-4 text-teal-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">$847K</div>
              <p className="text-xs text-muted-foreground">Next 30 days</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Stock-Out Risk</CardTitle>
              <AlertTriangle className="size-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">23 SKUs</div>
              <p className="text-xs text-muted-foreground">Needs reorder</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Top Sellers</CardTitle>
              <TrendingUp className="size-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">847</div>
              <p className="text-xs text-muted-foreground">Units predicted</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Inventory Turnover</CardTitle>
              <Package className="size-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">6.2x</div>
              <p className="text-xs text-muted-foreground">Per year</p>
            </CardContent>
          </Card>
        </div>

        {/* Forecast & Stock-Out Charts */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Sales Forecast vs Actual</CardTitle>
              <CardDescription>
                6-week prediction with historical comparison
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={forecastData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#0d9488"
                      strokeWidth={3}
                      name="Actual"
                    />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      stroke="#3b82f6"
                      strokeWidth={3}
                      strokeDasharray="5 5"
                      name="Forecast"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Stock-Out Risk by Category</CardTitle>
              <CardDescription>
                Number of SKUs at risk in each category
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stockOutData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="category" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Bar dataKey="risk" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top SKUs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top SKUs by Predicted Demand</CardTitle>
            <CardDescription>
              Items requiring attention based on forecasted demand and current
              stock
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left pb-3 text-sm">SKU</th>
                    <th className="text-left pb-3 text-sm">Product</th>
                    <th className="text-left pb-3 text-sm">Category</th>
                    <th className="text-right pb-3 text-sm">
                      Predicted Demand
                    </th>
                    <th className="text-right pb-3 text-sm">Current Stock</th>
                    <th className="text-right pb-3 text-sm">
                      Days to Stock-Out
                    </th>
                    <th className="text-right pb-3 text-sm">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {topSKUs.map((item) => (
                    <tr key={item.sku} className="border-b hover:bg-slate-50">
                      <td className="py-3">
                        <p className="text-sm text-muted-foreground">
                          {item.sku}
                        </p>
                      </td>
                      <td className="py-3">
                        <p className="text-sm">{item.name}</p>
                      </td>
                      <td className="py-3">
                        <p className="text-sm text-muted-foreground">
                          {item.category}
                        </p>
                      </td>
                      <td className="py-3 text-sm text-right">{item.demand}</td>
                      <td className="py-3 text-sm text-right">{item.stock}</td>
                      <td className="py-3 text-sm text-right">
                        {item.days} days
                      </td>
                      <td className="py-3 text-right">
                        <Badge
                          color={
                            item.risk === "High"
                              ? "red"
                              : item.risk === "Medium"
                                ? "orange"
                                : "green"
                          }
                        >
                          {item.risk}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Alert Banner */}
        <div className="rounded-md border border-orange-200 bg-orange-50 p-4">
          <div className="flex gap-3">
            <AlertTriangle className="size-5 text-orange-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm">
                <span className="font-medium">Action Required:</span> 3
                high-priority SKUs need immediate reorder
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                SKU-2847, SKU-5621, and SKU-9156 are predicted to stock out
                within 3 days. Review recommended order quantities.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Assistant Sidebar */}
      <div className="lg:sticky lg:top-6 lg:self-start">
        <ChatAssistant context="inventory-sales" />
      </div>
    </div>
  );
}
