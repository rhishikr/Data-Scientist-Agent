import * as React from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Badge } from "./ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Users, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";
import { ChatAssistant } from "./ChatAssistant";

type SegmentDatum = {
  name: string;
  value: number;
  color: string;
};

type CLVDatum = {
  month: string;
  value: number;
};

type Customer = {
  id: string;
  name: string;
  segment: "Top Buyer" | "Moderate" | "At-Risk";
  recency: string;
  frequency: number;
  monetary: string;
  churn: number; // 0..1
};

type ApiResponse = {
  range: { days: number; end: string };
  kpis: {
    activeCustomers: {
      value: number;
      deltaPct: number | null;
      deltaLabel: string;
    };
    avgCustomerValue: {
      value: number;
      deltaPct: number | null;
      deltaLabel: string;
    };
    churnRiskCustomers: {
      value: number;
      deltaPct: number | null;
      deltaLabel: string;
    };
    retentionRate: {
      value: number;
      deltaPct: number | null;
      deltaLabel: string;
    }; // 0..1
  };
  segments: { name: "Top Buyer" | "Moderate" | "At-Risk"; value: number }[];
  clvTrend: { month: string; value: number }[];
  topCustomers: {
    id: string;
    name: string;
    segment: "Top Buyer" | "Moderate" | "At-Risk";
    recencyDays: number;
    frequency: number;
    monetary: number;
    churnRisk: number; // 0..1 (ideally)
  }[];
};

function segmentBadgeClass(segment: Customer["segment"]): string {
  switch (segment) {
    case "Top Buyer":
      return "text-green-600 border-green-200";
    case "At-Risk":
      return "text-orange-600 border-orange-200";
    default:
      return "text-blue-600 border-blue-200";
  }
}

function churnBarClass(churn: number): string {
  if (churn > 0.7) return "bg-red-500";
  if (churn > 0.3) return "bg-orange-500";
  return "bg-green-500";
}

type PieLabelProps = {
  name?: string;
  value?: number;
};

function formatDelta(deltaPct: number | null): {
  icon: "up" | "down" | "none";
  text: string;
  cls: string;
} {
  if (deltaPct === null || Number.isNaN(deltaPct))
    return { icon: "none", text: "", cls: "text-muted-foreground" };
  const pct = Math.abs(deltaPct) * 100;
  if (deltaPct > 0)
    return { icon: "up", text: `+${pct.toFixed(1)}%`, cls: "text-green-600" };
  if (deltaPct < 0)
    return { icon: "down", text: `-${pct.toFixed(1)}%`, cls: "text-red-600" };
  return { icon: "none", text: "0.0%", cls: "text-muted-foreground" };
}

// IMPORTANT: your backend is currently returning some churnRisk values as 1 and tiny scientific numbers.
// Clamp to 0..1 to keep your UI stable.
function clamp01(x: number): number {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

export function CustomerInsightsScreen(): React.JSX.Element {
  const [dateRange, setDateRange] = React.useState<string>("30");

  const [data, setData] = React.useState<ApiResponse | null>(null);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const days = Number(dateRange);
    if (!Number.isFinite(days)) return;

    setLoading(true);
    setError(null);

    fetch(`http://127.0.0.1:8000/api/customer-insights?days=${days}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Backend error: HTTP ${r.status}`);
        return r.json();
      })
      .then((json: ApiResponse) => setData(json))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e)),
      )
      .finally(() => setLoading(false));
  }, [dateRange]);

  // Map backend → your existing UI shapes
  const segmentData: SegmentDatum[] = (data?.segments ?? []).map((s) => ({
    name: s.name === "Top Buyer" ? "Top Buyers" : s.name,
    value: s.value,
    color:
      s.name === "Top Buyer"
        ? "#10b981"
        : s.name === "At-Risk"
          ? "#f59e0b"
          : "#3b82f6",
  }));

  const clvData: CLVDatum[] = (data?.clvTrend ?? []).map((d) => ({
    month: d.month, // e.g. "2025-10" from backend (works fine)
    value: d.value,
  }));

  const topCustomers: Customer[] = (data?.topCustomers ?? []).map((c) => ({
    id: c.id,
    name: c.name,
    segment: c.segment,
    recency: `${c.recencyDays} days`,
    frequency: c.frequency,
    monetary: `$${Math.round(c.monetary).toLocaleString()}`,
    churn: clamp01(c.churnRisk),
  }));

  const activeDelta = formatDelta(data?.kpis.activeCustomers.deltaPct ?? null);
  const valueDelta = formatDelta(data?.kpis.avgCustomerValue.deltaPct ?? null);
  const churnDelta = formatDelta(
    data?.kpis.churnRiskCustomers.deltaPct ?? null,
  );
  const retentionDelta = formatDelta(data?.kpis.retentionRate.deltaPct ?? null);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
      {/* Main Content */}
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="mb-2">Customer Insights</h1>
            <p className="text-muted-foreground">
              AI-powered customer analytics and segmentation
            </p>
            {data?.range?.end && (
              <p className="text-xs text-muted-foreground mt-1">
                Data as of {data.range.end} • Last {data.range.days} days
              </p>
            )}
            {loading && (
              <p className="text-xs text-muted-foreground mt-1">
                Loading analytics…
              </p>
            )}
            {error && (
              <p className="text-xs text-red-600 mt-1">
                Failed to load: {error}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Date range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="365">Last year</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Active Customers</CardTitle>
              <Users className="size-4 text-teal-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {data ? data.kpis.activeCustomers.value.toLocaleString() : "—"}
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {activeDelta.icon === "up" && (
                  <TrendingUp className="size-3 text-green-600" />
                )}
                {activeDelta.icon === "down" && (
                  <TrendingDown className="size-3 text-red-600" />
                )}
                {activeDelta.text ? (
                  <span className={activeDelta.cls}>{activeDelta.text}</span>
                ) : (
                  <span>—</span>
                )}
                <span>
                  {data?.kpis.activeCustomers.deltaLabel ??
                    "vs previous period"}
                </span>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Avg Customer Value</CardTitle>
              <TrendingUp className="size-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {data
                  ? `$${Math.round(data.kpis.avgCustomerValue.value).toLocaleString()}`
                  : "—"}
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {valueDelta.icon === "up" && (
                  <TrendingUp className="size-3 text-green-600" />
                )}
                {valueDelta.icon === "down" && (
                  <TrendingDown className="size-3 text-red-600" />
                )}
                {valueDelta.text ? (
                  <span className={valueDelta.cls}>{valueDelta.text}</span>
                ) : (
                  <span>—</span>
                )}
                <span>
                  {data?.kpis.avgCustomerValue.deltaLabel ??
                    "vs previous period"}
                </span>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Churn-Risk Customers</CardTitle>
              <AlertTriangle className="size-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {data
                  ? data.kpis.churnRiskCustomers.value.toLocaleString()
                  : "—"}
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {churnDelta.icon === "up" && (
                  <TrendingUp className="size-3 text-green-600" />
                )}
                {churnDelta.icon === "down" && (
                  <TrendingDown className="size-3 text-red-600" />
                )}
                {churnDelta.text ? (
                  <span className={churnDelta.cls}>{churnDelta.text}</span>
                ) : (
                  <span>—</span>
                )}
                <span>
                  {data?.kpis.churnRiskCustomers.deltaLabel ??
                    "needs attention"}
                </span>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm">Retention Rate</CardTitle>
              <Users className="size-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl">
                {data
                  ? `${(data.kpis.retentionRate.value * 100).toFixed(1)}%`
                  : "—"}
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {retentionDelta.icon === "up" && (
                  <TrendingUp className="size-3 text-green-600" />
                )}
                {retentionDelta.icon === "down" && (
                  <TrendingDown className="size-3 text-red-600" />
                )}
                {retentionDelta.text ? (
                  <span className={retentionDelta.cls}>
                    {retentionDelta.text}
                  </span>
                ) : (
                  <span>—</span>
                )}
                <span>
                  {data?.kpis.retentionRate.deltaLabel ?? "vs previous period"}
                </span>
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Customer Segments & CLV Charts */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Customer Segments</CardTitle>
              <CardDescription>
                Distribution by purchase behavior
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={segmentData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry: PieLabelProps) =>
                        `${entry.name ?? ""}: ${typeof entry.value === "number" ? entry.value : ""}`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {segmentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="flex justify-center gap-4 mt-4">
                {segmentData.map((segment) => (
                  <div key={segment.name} className="flex items-center gap-2">
                    <div
                      className="size-3 rounded-full"
                      style={{ backgroundColor: segment.color }}
                    />
                    <span className="text-sm text-muted-foreground">
                      {segment.name}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Customer Lifetime Value Trend</CardTitle>
              <CardDescription>
                Average CLV over the last 6 months
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={clvData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#0d9488"
                      strokeWidth={3}
                      dot={{ fill: "#0d9488", r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top Customers Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top Customers</CardTitle>
            <CardDescription>
              Ranked by customer lifetime value and engagement
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left pb-3 text-sm">Customer</th>
                    <th className="text-left pb-3 text-sm">Segment</th>
                    <th className="text-left pb-3 text-sm">Recency</th>
                    <th className="text-right pb-3 text-sm">Frequency</th>
                    <th className="text-right pb-3 text-sm">Monetary</th>
                    <th className="text-right pb-3 text-sm">Churn Risk</th>
                  </tr>
                </thead>

                <tbody>
                  {topCustomers.map((customer) => (
                    <tr
                      key={customer.id}
                      className="border-b hover:bg-slate-50"
                    >
                      <td className="py-3">
                        <div>
                          <p className="text-sm">{customer.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {customer.id}
                          </p>
                        </div>
                      </td>

                      <td className="py-3">
                        <Badge
                          variant="outline"
                          className={segmentBadgeClass(customer.segment)}
                        >
                          {customer.segment}
                        </Badge>
                      </td>

                      <td className="py-3 text-sm text-muted-foreground">
                        {customer.recency}
                      </td>
                      <td className="py-3 text-sm text-right">
                        {customer.frequency}
                      </td>
                      <td className="py-3 text-sm text-right">
                        {customer.monetary}
                      </td>

                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${churnBarClass(customer.churn)}`}
                              style={{
                                width: `${clamp01(customer.churn) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-10">
                            {(clamp01(customer.churn) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}

                  {!loading && topCustomers.length === 0 && (
                    <tr>
                      <td
                        className="py-6 text-sm text-muted-foreground"
                        colSpan={6}
                      >
                        No customers found for this range.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chat Assistant Sidebar (unchanged) */}
      <div className="lg:sticky lg:top-6 lg:self-start">
        <ChatAssistant context="customer-insights" />
      </div>
    </div>
  );
}
