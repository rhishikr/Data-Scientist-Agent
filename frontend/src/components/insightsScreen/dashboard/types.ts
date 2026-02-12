// dashboard/types.ts

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

export type Snapshot = {
  meta?: {
    generated_at?: string;
    as_of?: string;
    datasets_used?: string[];
  };
  kpis?: any;
};

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
