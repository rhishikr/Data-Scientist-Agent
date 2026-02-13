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
