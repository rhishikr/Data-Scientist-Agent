// dashboard/types.ts
import type React from "react";

// ------------------------
// Core KPI snapshot types
// ------------------------
export type KpiCardRow = {
  id: string;
  title: string;
  value: number;
  unit?: string;
  format?: "currency" | "percent" | "number" | "minutes";
  group?: string;
};

export type CustomerRow = {
  customer_id: string;
  name: string;
  location?: string;
  device_type?: string;
  total_orders: number;
  total_spend: number;
  avg_order_value?: number;
  recency_days?: number;
  top_product_id?: string;
};

export type SnapshotMeta = {
  generated_at?: string;
  as_of?: string;
  datasets_used?: string[];
};

export type SnapshotTables = {
  top_customers?: CustomerRow[];
  products?: any[];
  [key: string]: any;
};

export type Snapshot = {
  meta?: SnapshotMeta;
  kpis?: any;

  // API returns these
  cards?: KpiCardRow[];
  tables?: SnapshotTables;
};

// ------------------------
// Widget system types
// ------------------------
export type WidgetSize = "small" | "medium" | "large";
export type WidgetType = "card" | "chart" | "table";
export type WidgetCategory = "Customer" | "Product & Sales" | "Marketing / Growth";

export interface WidgetDefinition {
  id: string;
  title: string;
  description: string;
  type: WidgetType;
  defaultSize: WidgetSize;
  category: WidgetCategory;
  icon: any;
  render: () => React.ReactNode;
}

// ------------------------
// Forecast snapshot types
// ------------------------
export type ForecastMeta = SnapshotMeta;

export type ForecastedRevenue = {
  as_of?: string;
  next_7d?: number;
  next_30d?: number;
  next_90d?: number;
  series_daily_path?: string;
  metrics?: {
    mae?: number;
    mape?: number;
    train_rows?: number;
    test_rows?: number;
  };
};

export type ForecastedDemandPerSku = {
  error?: string;
};

export type ExpectedChurnNextMonth = {
  as_of?: string;
  snapshot_date?: string;
  expected_churn_rate_next_30d?: number;
  top_customers_path?: string;
  definition?: string;
  metrics?: {
    roc_auc?: number;
    avg_precision?: number;
    train_rows?: number;
    test_rows?: number;
    positive_rate_train?: number;
    positive_rate_test?: number;
  };
};

export type ProjectedCashflow = {
  as_of?: string;
  next_30d_cash_proxy?: number;
  series_daily_path?: string;
  note?: string;
  metrics?: {
    mae?: number;
    train_rows?: number;
    test_rows?: number;
    note?: string;
  };
};

// IMPORTANT: your JSON has top_3_risks/opps as objects { title, evidence }
export type ExecutiveInsightItem = {
  title: string;
  evidence?: any;
};

export type ExecutiveInsights = {
  key_drivers_of_growth_decline?: string[];
  top_3_risks?: ExecutiveInsightItem[];
  top_3_opportunities?: ExecutiveInsightItem[];
  recommended_actions_rule_based?: string[];
  recommended_actions_llm_context?: {
    what_to_do?: string;
    constraints?: string[];
    evidence?: any;
    example_style?: string;
  };
  summary?: string[];
};

export type ForecastSnapshot = {
  meta?: ForecastMeta;
  forecasts?: {
    forecasted_revenue?: ForecastedRevenue;
    forecasted_demand_per_sku?: ForecastedDemandPerSku;
    expected_churn_next_month?: ExpectedChurnNextMonth;
    projected_cashflow?: ProjectedCashflow;
  };
  executive_insights?: ExecutiveInsights;
};

// ------------------------
// Insight types (from /api/insights/snapshot)
// ------------------------
export type Insight = {
  insight_id: string;
  title: string;
  description: string;
  evidence: Record<string, any>;
  recommendation: string;
  severity: "low" | "medium" | "high";
  confidence: number;
  datasets_used?: string[];
  hypothesis_support?: Array<Record<string, any>>;
  tags?: string[];
  created_at?: string;
  // Action metadata (retail doctor)
  action_type?: string;
  impact_estimate?: string;
  effort?: "quick-win" | "moderate" | "strategic";
  priority?: number;
};

export type InsightsSnapshot = {
  meta?: { generated_at?: string; datasets_used?: string[]; num_insights?: number };
  insights: Insight[];
  validation?: Record<string, string[]>;
};

// ------------------------
// Revenue forecast series (from /api/forecast/series/revenue)
// ------------------------
export type RevenueForecastPoint = {
  date: string;
  revenue_actual?: number;
  revenue_forecast?: number;
};

// ------------------------
// Demand forecast per SKU (from /api/forecast/series/demand)
// ------------------------
export type DemandForecastSku = {
  sku: string;
  name?: string;
  category?: string;
  brand?: string;
  forecast_qty_30d: number;
  avg_daily_forecast: number;
  current_stock: number;
  reorder_threshold: number;
  days_until_stockout: number | null;
  status: "critical" | "warning" | "healthy" | "unknown";
};

// ------------------------
// Churn prediction (from /api/forecast/series/churn)
// ------------------------
export type ChurnPrediction = {
  customer_id: string;
  name?: string;
  churn_prob_30d: number;
  total_spend?: number;
  recency_days?: number;
  total_orders?: number;
  segment?: string;
};

// ------------------------
// AI Analysis (from /api/insights/ai-analysis)
// ------------------------
export type AiAnalysis = {
  analysis: string | null;
  key_findings: string[];
  recommendations: string[];
  risks: string[];
  generated_at?: string;
  cached?: boolean;
  error?: string;
};

// ------------------------
// Prescription / Action Plan (Retail Doctor)
// ------------------------
export type PrescriptionStatus = "pending" | "done" | "dismissed";

export type Prescription = {
  id: string;
  priority: number;
  category: "inventory" | "customer" | "revenue" | "marketing" | "product" | "funnel" | "pricing";
  urgency: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  impact_estimate: string;
  effort: string;
  evidence: Record<string, any>;
  source: string;
  action_type: string;
  related_entities: string[];
  status?: PrescriptionStatus;
};

export type ActionPlan = {
  health_score: number;
  health_summary: string;
  prescriptions: Prescription[];
  generated_at: string;
  segment_recommendations?: Record<string, string[]>;
};

// ------------------------
// Location stock analysis
// ------------------------
export type LocationSummary = {
  location: string;
  total_skus: number;
  total_stock: number;
  avg_stock: number;
};

export type StoreTransfer = {
  sku: string;
  product_name: string;
  category: string;
  from_location: string;
  from_stock: number;
  to_location: string;
  to_stock: number;
  transfer_qty: number;
  to_days_left: number;
  urgency: "critical" | "warning";
};

// ------------------------
// Chart Narratives
// ------------------------
export type ChartNarrativeData = {
  narrative: string;
  action_hint: string;
};

export type ChartNarratives = {
  narratives: Record<string, ChartNarrativeData>;
  generated_at?: string;
  cached?: boolean;
  error?: string;
};

// ------------------------
// Run Comparison (from /api/runs/compare)
// ------------------------
export type KpiDelta = {
  id: string;
  title: string;
  group: string;
  format: string;
  current_value: number;
  previous_value: number | null;
  absolute_change: number | null;
  percent_change: number | null;
  direction: "up" | "down" | "stable" | "new";
};

export type ResolvedIssue = {
  title: string;
  severity: string;
  description?: string;
};

export type CompletedPrescription = {
  id: string;
  title: string;
  category: string;
  urgency: string;
  related_kpi_changes: Array<{
    id: string;
    title: string;
    direction: string;
    percent_change: number | null;
  }>;
};

export type RunComparison = {
  current_snapshot: { generated_at?: string } | null;
  previous_snapshot: { generated_at?: string } | null;
  deltas: KpiDelta[];
  resolved_issues?: ResolvedIssue[];
  new_risks?: ResolvedIssue[];
  completed_prescriptions?: CompletedPrescription[];
  message?: string;
  error?: string;
};

// ------------------------
// AI Comparison Analysis (from /api/runs/compare/ai-analysis)
// ------------------------
export type DepartmentGrade = {
  department: string;
  grade: string;
  trend: "improving" | "stable" | "declining";
  one_liner: string;
};

export type RootCause = {
  metric: string;
  direction: string;
  explanation: string;
  contributing_factors: string[];
};

export type CausalChain = {
  chain: string[];
  narrative: string;
};

export type RevenueBridgeComponent = {
  label: string;
  impact: number;
};

export type PrescriptionVerdict = {
  prescription_title: string;
  verdict: "effective" | "partially_effective" | "no_impact" | "too_early";
  evidence: string;
  related_kpi_impact: string;
};

export type MissedOpportunity = {
  prescription_title: string;
  status: string;
  estimated_cost_of_inaction: string;
  urgency_now: string;
};

export type Target30Day = {
  target: string;
  current_value: string;
  target_value: string;
  how: string;
  expected_impact: string;
};

export type QuickWin = {
  action: string;
  effort: string;
  expected_impact: string;
  data_point: string;
};

export type Anomaly = {
  metric: string;
  change: string;
  why_unexpected: string;
  suggested_investigation: string;
};

export type ComparisonAiAnalysis = {
  executive_summary: string | null;
  department_grades: DepartmentGrade[];
  root_causes: RootCause[];
  causal_chains: CausalChain[];
  revenue_bridge: {
    total_change: number;
    components: RevenueBridgeComponent[];
  } | null;
  profit_loss_drivers: { positive: string[]; negative: string[] };
  prescription_report_card: PrescriptionVerdict[];
  missed_opportunities: MissedOpportunity[];
  next_30_day_targets: Target30Day[];
  quick_wins: QuickWin[];
  start_doing: string[];
  stop_doing: string[];
  keep_doing: string[];
  anomalies: Anomaly[];
  trend_verdict: {
    direction: "improving" | "stable" | "declining";
    confidence: "high" | "medium" | "low";
    summary: string;
  } | null;
  generated_at?: string;
  cached?: boolean;
  error?: string;
};

// ------------------------
// Funnel & Sessions (from /api/funnel/snapshot, /api/sessions/analytics)
// ------------------------
export type FunnelSnapshot = {
  funnel_kpis: Record<string, any>;
  daily_trends: Array<{
    date: string;
    sessions?: number;
    product_views?: number;
    add_to_cart?: number;
    begin_checkout?: number;
    purchases?: number;
    conversion_rate?: number;
    cart_abandonment_rate?: number;
  }>;
};

export type SessionsAnalytics = {
  by_device: Record<string, number>;
  conversion_by_device: Record<string, number>;
  avg_revenue_by_device: Record<string, number>;
  by_traffic_source: Record<string, number>;
  conversion_by_source: Record<string, number>;
  by_landing_page: Record<string, number>;
  conversion_by_landing: Record<string, number>;
  session_duration_distribution: Record<string, number>;
  session_duration_conversion: Record<string, number>;
};
