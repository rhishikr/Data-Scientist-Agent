// dashboard/data.ts
import { useCallback, useEffect, useState } from "react";
import type { Snapshot, KpiCardRow, CustomerRow, ForecastSnapshot } from "./types";

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
