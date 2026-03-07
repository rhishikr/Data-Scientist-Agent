import React, { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Input } from "../../ui/input";
import type { ActionPlan, Prescription } from "../dashboard/types";
import { HealthGauge } from "../charts/HealthGauge";
import { PrescriptionCard } from "../charts/PrescriptionCard";

const CATEGORY_FILTERS = ["all", "inventory", "customer", "revenue", "marketing", "product"] as const;

interface ActionQueueTabProps {
  actionPlan: ActionPlan | null;
  loading?: boolean;
}

export function ActionQueueTab({ actionPlan, loading }: ActionQueueTabProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const prescriptions = actionPlan?.prescriptions ?? [];

  const filtered = useMemo(() => {
    let result = prescriptions;
    if (categoryFilter !== "all") {
      result = result.filter((p) => p.category === categoryFilter);
    }
if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      );
    }
    return result;
  }, [prescriptions, categoryFilter, search]);

  const urgencyCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const p of prescriptions) {
      counts[p.urgency] = (counts[p.urgency] ?? 0) + 1;
    }
    return counts;
  }, [prescriptions]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-32 rounded-xl bg-muted animate-pulse" />
        <div className="h-24 rounded-xl bg-muted animate-pulse" />
        <div className="h-24 rounded-xl bg-muted animate-pulse" />
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
              <h3 className="text-lg font-semibold">Store Health</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {actionPlan.health_summary}
              </p>
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

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search actions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Category filter */}
        <div className="flex items-center gap-1">
          {CATEGORY_FILTERS.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                categoryFilter === cat
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {cat === "all" ? "All" : cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Prescription cards */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No actions match your filters.
            </CardContent>
          </Card>
        ) : (
          filtered.map((p) => <PrescriptionCard key={p.id} prescription={p} />)
        )}
      </div>
    </div>
  );
}
