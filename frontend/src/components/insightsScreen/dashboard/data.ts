// dashboard/data.ts
import { useCallback, useEffect, useState } from "react";
import type {
  Snapshot, KpiCardRow, CustomerRow, ForecastSnapshot,
  InsightsSnapshot, RevenueForecastPoint, DemandForecastSku,
  ChurnPrediction, AiAnalysis, ActionPlan, ChartNarratives,
  LocationSummary, StoreTransfer,
} from "./types";

const API_BASE = "http://127.0.0.1:8000";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Request failed ${res.status} ${res.statusText}: ${text}`);
  }

  return (await res.json()) as T;
}

export type DashboardData = {
  snapshot: Snapshot | null;
  cards: KpiCardRow[];
  customers: CustomerRow[];
  products: any[];
  forecastSnapshot: ForecastSnapshot | null;
};

export function useDashboardData(runId?: string | null) {
  const [data, setData] = useState<DashboardData>({
    snapshot: null,
    cards: [],
    customers: [],
    products: [],
    forecastSnapshot: null,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const [snap, forecastSnap] = await Promise.all([
        fetchJson<Snapshot>(`${API_BASE}/api/kpi/snapshot${qs}`),
        fetchJson<ForecastSnapshot>(`${API_BASE}/api/forecast/snapshot${qs}`),
      ]);

      const cards = Array.isArray(snap?.cards) ? snap.cards : [];

      const customers = Array.isArray(snap?.tables?.top_customers)
        ? snap.tables!.top_customers!
        : [];

      const products =
        (Array.isArray(snap?.tables?.products) && snap.tables!.products!) ||
        (Array.isArray((snap as any)?.tables?.inventory_risk_products) &&
          (snap as any).tables.inventory_risk_products) ||
        [];

      setData({
        snapshot: snap,
        cards,
        customers,
        products,
        forecastSnapshot: forecastSnap,
      });
    } catch (e: any) {
      setError(e?.message ?? "Failed to load dashboard data");
      setData({
        snapshot: null,
        cards: [],
        customers: [],
        products: [],
        forecastSnapshot: null,
      });
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...data, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Pipeline runs
// ---------------------------------------------------------------------------

export type PipelineRun = {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  duration_seconds: number | null;
};

export function useRuns() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJson<PipelineRun[]>(`${API_BASE}/api/runs`);
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { runs, loading, refresh };
}

// ---------------------------------------------------------------------------
// Cleaned / Featured data
// ---------------------------------------------------------------------------

export type DatasetPreview = {
  table_name: string;
  row_count: number;
  column_count: number;
  preview_rows: Record<string, any>[];
  column_stats: Record<string, any>;
  storage_path: string;
  download_url: string;
};

export type CleanedDataResponse = {
  run_id?: string;
  tables: DatasetPreview[];
  report: Record<string, any>;
  error?: string;
};

export type FeaturedDataResponse = CleanedDataResponse;

export function useCleanedData(runId?: string | null) {
  const [data, setData] = useState<CleanedDataResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<CleanedDataResponse>(
        `${API_BASE}/api/cleaned-data${qs}`
      );
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, refresh };
}

// ---------------------------------------------------------------------------
// Insights snapshot
// ---------------------------------------------------------------------------

export function useInsightsData(runId?: string | null) {
  const [data, setData] = useState<InsightsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<InsightsSnapshot>(
        `${API_BASE}/api/insights/snapshot${qs}`
      );
      setData(result);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load insights");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Revenue forecast series
// ---------------------------------------------------------------------------

export function useRevenueForecastSeries(runId?: string | null) {
  const [series, setSeries] = useState<RevenueForecastPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<{ series: RevenueForecastPoint[] }>(
        `${API_BASE}/api/forecast/series/revenue${qs}`
      );
      setSeries(result.series || []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load revenue series");
      setSeries([]);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { series, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Demand forecast per SKU
// ---------------------------------------------------------------------------

export function useDemandForecast(runId?: string | null) {
  const [skus, setSkus] = useState<DemandForecastSku[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<{ skus: DemandForecastSku[] }>(
        `${API_BASE}/api/forecast/series/demand${qs}`
      );
      setSkus(result.skus || []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load demand forecast");
      setSkus([]);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { skus, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Churn predictions
// ---------------------------------------------------------------------------

export function useChurnPredictions(runId?: string | null) {
  const [customers, setCustomers] = useState<ChurnPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<{ customers: ChurnPrediction[] }>(
        `${API_BASE}/api/forecast/series/churn${qs}`
      );
      setCustomers(result.customers || []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load churn predictions");
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { customers, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// AI analysis (auto-cached per run)
// ---------------------------------------------------------------------------

export function useAiAnalysis(runId?: string | null) {
  const [data, setData] = useState<AiAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<AiAnalysis>(
        `${API_BASE}/api/insights/ai-analysis${qs}`
      );
      setData(result);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load AI analysis");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Action Plan (Retail Doctor)
// ---------------------------------------------------------------------------

export function useActionPlan(runId?: string | null) {
  const [data, setData] = useState<ActionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<ActionPlan>(
        `${API_BASE}/api/action-plan${qs}`
      );
      setData(result);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load action plan");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, error, refresh };
}

// ---------------------------------------------------------------------------
// Chart Narratives
// ---------------------------------------------------------------------------

export function useChartNarratives(runId?: string | null) {
  const [data, setData] = useState<ChartNarratives | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<ChartNarratives>(
        `${API_BASE}/api/chart-narratives${qs}`
      );
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, refresh };
}

// ---------------------------------------------------------------------------
// Featured data
// ---------------------------------------------------------------------------

export function useFeaturedData(runId?: string | null) {
  const [data, setData] = useState<FeaturedDataResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<FeaturedDataResponse>(
        `${API_BASE}/api/featured-data${qs}`
      );
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, refresh };
}

// ---------------------------------------------------------------------------
// Location stock analysis
// ---------------------------------------------------------------------------

export type LocationStockData = {
  locations: LocationSummary[];
  transfers: StoreTransfer[];
};

export function useLocationStock(runId?: string | null) {
  const [data, setData] = useState<LocationStockData>({ locations: [], transfers: [] });
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const qs = runId ? `?run_id=${runId}` : "";
      const result = await fetchJson<LocationStockData & { error?: string }>(
        `${API_BASE}/api/forecast/series/demand-by-location${qs}`
      );
      setData({
        locations: result.locations || [],
        transfers: result.transfers || [],
      });
    } catch {
      setData({ locations: [], transfers: [] });
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => { refresh(); }, [refresh]);
  return { ...data, loading, refresh };
}
