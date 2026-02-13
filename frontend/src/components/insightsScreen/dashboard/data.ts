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

export function useDashboardData() {
  const [data, setData] = useState<DashboardData>({
    snapshot: null,
    cards: [],
    customers: [],
    products: [],
    forecastSnapshot: null, // ✅ add
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [snap, forecastSnap] = await Promise.all([
        fetchJson<Snapshot>(`${API_BASE}/api/kpi/snapshot`),
        fetchJson<ForecastSnapshot>(`${API_BASE}/api/forecast/snapshot`),
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
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...data, loading, error, refresh };
}
