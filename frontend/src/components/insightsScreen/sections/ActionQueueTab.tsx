import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";

import { Card, CardContent } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Input } from "../../ui/input";
import type { ActionPlan, Prescription, PrescriptionStatus } from "../dashboard/types";
import { HealthGauge } from "../charts/HealthGauge";
import { PrescriptionCard } from "../charts/PrescriptionCard";

import { API_BASE, apiFetch } from "../../../lib/api";

const STATUS_FILTERS = ["pending", "done", "dismissed"] as const;

interface ActionQueueTabProps {
  actionPlan: ActionPlan | null;
  loading?: boolean;
  runId?: string | null;
}

export function ActionQueueTab({ actionPlan, loading, runId }: ActionQueueTabProps) {
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [search, setSearch] = useState("");
  const [statuses, setStatuses] = useState<Record<string, PrescriptionStatus>>({});

  // Sliding pill indicator
  const pillContainerRef = useRef<HTMLDivElement>(null);
  const pillButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [pillStyle, setPillStyle] = useState<{ left: number; width: number }>({ left: 0, width: 0 });
  const pillReady = useRef(false);

  useLayoutEffect(() => {
    const container = pillContainerRef.current;
    const activeBtn = pillButtonRefs.current.get(statusFilter);
    if (container && activeBtn) {
      const containerRect = container.getBoundingClientRect();
      const btnRect = activeBtn.getBoundingClientRect();
      setPillStyle({
        left: btnRect.left - containerRect.left,
        width: btnRect.width,
      });
      pillReady.current = true;
    }
  }, [statusFilter, loading, actionPlan]);

  // Fetch saved statuses on mount
  useEffect(() => {
    const url = runId
      ? `${API_BASE}/api/action-plan/prescriptions/statuses?run_id=${runId}`
      : `${API_BASE}/api/action-plan/prescriptions/statuses`;
    apiFetch(url)
      .then((r) => r.json())
      .then((data) => {
        const map: Record<string, PrescriptionStatus> = {};
        for (const s of data.statuses ?? []) {
          map[s.prescription_id] = s.status as PrescriptionStatus;
        }
        setStatuses(map);
      })
      .catch(() => {});
  }, [runId]);

  // Merge statuses into prescriptions
  const prescriptions: Prescription[] = useMemo(() => {
    return (actionPlan?.prescriptions ?? []).map((p) => ({
      ...p,
      status: statuses[p.id] ?? p.status ?? "pending",
    }));
  }, [actionPlan, statuses]);

  const handleStatusChange = useCallback(
    (id: string, status: PrescriptionStatus) => {
      // Optimistic update
      setStatuses((prev) => ({ ...prev, [id]: status }));
      // Persist to backend
      apiFetch(`${API_BASE}/api/action-plan/prescriptions/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, run_id: runId ?? undefined }),
      }).catch(() => {});
    },
    [runId],
  );

  const filtered = useMemo(() => {
    let result = prescriptions;
    if (statusFilter !== "all") {
      result = result.filter((p) => (p.status ?? "pending") === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q),
      );
    }
    return result;
  }, [prescriptions, statusFilter, search]);

  const urgencyCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const p of prescriptions) {
      counts[p.urgency] = (counts[p.urgency] ?? 0) + 1;
    }
    return counts;
  }, [prescriptions]);

  const completedCount = useMemo(
    () => prescriptions.filter((p) => p.status === "done").length,
    [prescriptions],
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-32 rounded-md bg-muted animate-pulse" />
        <div className="h-24 rounded-md bg-muted animate-pulse" />
        <div className="h-24 rounded-md bg-muted animate-pulse" />
      </div>
    );
  }

  if (!actionPlan) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          No action plan available. Run the pipeline to generate recommendations.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Health score hero */}
      <Card>
        <CardContent className="py-6">
          <div className="flex items-center gap-6">
            <div className="relative">
              <HealthGauge score={actionPlan.health_score} size={110} />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">Store Health</h3>
                {prescriptions.length > 0 && (
                  <span className="text-sm text-muted-foreground">
                    {completedCount}/{prescriptions.length} completed
                  </span>
                )}
              </div>
              <div
                className="text-sm leading-loose text-gray-700"
                dangerouslySetInnerHTML={{ __html: actionPlan.health_summary }}
              />
              {/* Progress bar */}
              {prescriptions.length > 0 && (
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-green-500 transition-all duration-300"
                      style={{ width: `${(completedCount / prescriptions.length) * 100}%` }}
                    />
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2 flex-wrap">
                {urgencyCounts.critical > 0 && (
                  <Badge color="red">
                    {urgencyCounts.critical} Critical
                  </Badge>
                )}
                {urgencyCounts.high > 0 && (
                  <Badge color="orange">
                    {urgencyCounts.high} High Priority
                  </Badge>
                )}
                {urgencyCounts.medium > 0 && (
                  <Badge color="blue">
                    {urgencyCounts.medium} Recommended
                  </Badge>
                )}
                {urgencyCounts.low > 0 && (
                  <Badge color="green">
                    {urgencyCounts.low} Low Priority
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Toolbar: label + status pills + search */}
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold whitespace-nowrap">Action Queue</h3>

        <div ref={pillContainerRef} className="relative flex items-center rounded-md bg-muted p-1">
          <div
            className={`absolute rounded-md bg-background shadow-sm ${pillReady.current ? "transition-all duration-300 ease-in-out" : ""}`}
            style={{ left: pillStyle.left, width: pillStyle.width, top: 4, bottom: 4 }}
          />
          {STATUS_FILTERS.map((s) => (
            <button
              type="button"
              key={s}
              ref={(el) => { if (el) pillButtonRefs.current.set(s, el); }}
              onClick={() => setStatusFilter(s)}
              className={`relative z-10 rounded-md px-4 py-1.5 text-xs font-medium transition-colors duration-300 cursor-pointer ${
                statusFilter === s
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search actions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 w-48"
          />
        </div>
      </div>

      {/* Prescription cards */}
      {filtered.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No actions match your filters.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((p) => (
            <PrescriptionCard
              key={p.id}
              prescription={p}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}
