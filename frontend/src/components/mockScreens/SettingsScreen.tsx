import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Input } from "../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import { Badge } from "../ui/badge";
import { Separator } from "../ui/separator";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "../ui/collapsible";
import {
  Database,
  RefreshCw,
  Trash2,
  Plus,
  Loader2,
  ChevronDown,
  ListChecks,
} from "lucide-react";
import { API_BASE, apiFetch } from "../../lib/api";

const SCENARIOS = [
  { value: "organic-growth", label: "Organic Growth", description: "Steady healthy growth across all metrics" },
  { value: "profit", label: "Profit", description: "High conversions, low returns, strong margins" },
  { value: "loss", label: "Loss", description: "Low conversions, high returns and cancellations" },
  { value: "seasonal-spike", label: "Seasonal Spike", description: "Holiday/flash sale: 4x volume, heavy discounts" },
  { value: "stockout-crisis", label: "Stockout Crisis", description: "Supply chain problems, inventory drains" },
  { value: "marketing-blitz", label: "Marketing Blitz", description: "Aggressive ad campaign, 5x spend" },
  { value: "churn-wave", label: "Churn Wave", description: "Customer exodus, low engagement" },
  { value: "new-product-launch", label: "New Product Launch", description: "Concentrated demand on newest SKUs" },
];

interface DataStats {
  [key: string]: number;
}

export function SettingsScreen() {
  const [stats, setStats] = useState<DataStats>({});
  const [loadingStats, setLoadingStats] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showGenerateConfirm, setShowGenerateConfirm] = useState(false);
  const [updateDays, setUpdateDays] = useState(7);
  const [updateScenario, setUpdateScenario] = useState("organic-growth");
  const [statsOpen, setStatsOpen] = useState(false);

  // Pipeline run management state
  const [runs, setRuns] = useState<
    Array<{ id: string; started_at: string; status: string; duration_seconds: number | null }>
  >([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [selectedRunIds, setSelectedRunIds] = useState<Set<string>>(new Set());
  const [deletingRuns, setDeletingRuns] = useState(false);
  const [showDeleteRunConfirm, setShowDeleteRunConfirm] = useState(false);

  const fetchRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/runs`);
      const data = await res.json();
      setRuns(Array.isArray(data) ? data : []);
    } catch {
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/data/status`);
      const data = await res.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch {
      // Stats loading failed silently
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRuns();
  }, [fetchStats, fetchRuns]);

  const totalRows = stats._total ?? 0;
  const hasData = totalRows > 0;

  const handleGenerate = async () => {
    setShowGenerateConfirm(false);
    setGenerating(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/data/generate`, { method: "POST" });
      const data = await res.json();
      if (data.success) {
        toast.success("Data generated successfully");
        fetchStats();
      } else {
        toast.error(`Generation failed: ${data.message}`);
      }
    } catch (err) {
      toast.error(`Generation failed: ${err}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleUpdate = async () => {
    setShowUpdateModal(false);
    setUpdating(true);
    try {
      const res = await apiFetch(
        `${API_BASE}/api/data/update?days=${updateDays}&scenario=${updateScenario}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        fetchStats();
      } else {
        toast.error(`Update failed: ${data.message}`);
      }
    } catch (err) {
      toast.error(`Update failed: ${err}`);
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    setShowDeleteConfirm(false);
    setDeleting(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/data/delete`, { method: "DELETE" });
      const data = await res.json();
      if (data.success) {
        toast.success(data.message);
        fetchStats();
      } else {
        toast.error(`Delete failed: ${data.message}`);
      }
    } catch (err) {
      toast.error(`Delete failed: ${err}`);
    } finally {
      setDeleting(false);
    }
  };

  const hasRunningSelected = runs.some(
    (r) => selectedRunIds.has(r.id) && r.status === "running"
  );

  const toggleRunId = (id: string) => {
    setSelectedRunIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedRunIds.size === runs.length) {
      setSelectedRunIds(new Set());
    } else {
      setSelectedRunIds(new Set(runs.map((r) => r.id)));
    }
  };

  const handleDeleteRuns = async () => {
    if (selectedRunIds.size === 0) return;
    setShowDeleteRunConfirm(false);
    setDeletingRuns(true);
    let succeeded = 0;
    let failed = 0;
    for (const runId of selectedRunIds) {
      try {
        const res = await apiFetch(`${API_BASE}/api/runs/${runId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) succeeded++;
        else failed++;
      } catch {
        failed++;
      }
    }
    if (succeeded > 0) toast.success(`Deleted ${succeeded} pipeline run${succeeded > 1 ? "s" : ""}`);
    if (failed > 0) toast.error(`Failed to delete ${failed} run${failed > 1 ? "s" : ""}`);
    setSelectedRunIds(new Set());
    fetchRuns();
    setDeletingRuns(false);
  };

  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-xs text-muted-foreground">
          Manage raw data in Supabase
        </p>
      </div>

      <div className="p-6 max-w-4xl space-y-6">
        {/* Data Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="size-5" />
              Data Management
            </CardTitle>
            <CardDescription>
              Generate, update, or delete raw retail data stored in Supabase
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              {/* Generate Button */}
              <Button
                onClick={() => setShowGenerateConfirm(true)}
                disabled={generating || updating || deleting}
                className="bg-teal-600 hover:bg-teal-700"
              >
                {generating ? (
                  <Loader2 className="size-4 mr-2 animate-spin" />
                ) : (
                  <Plus className="size-4 mr-2" />
                )}
                {generating ? "Generating..." : "Generate Data"}
              </Button>

              {/* Update Button */}
              <Button
                variant="outline"
                onClick={() => setShowUpdateModal(true)}
                disabled={generating || updating || deleting || !hasData}
              >
                {updating ? (
                  <Loader2 className="size-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="size-4 mr-2" />
                )}
                {updating ? "Updating..." : "Update Data"}
              </Button>

              {/* Delete Button */}
              <Button
                variant="destructive"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={generating || updating || deleting || !hasData}
              >
                {deleting ? (
                  <Loader2 className="size-4 mr-2 animate-spin" />
                ) : (
                  <Trash2 className="size-4 mr-2" />
                )}
                {deleting ? "Deleting..." : "Delete Data"}
              </Button>
            </div>

            <Separator />

            {/* Data Stats */}
            <Collapsible open={statsOpen} onOpenChange={setStatsOpen}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium w-full group">
                <ChevronDown className="size-4 transition-transform duration-200" style={{ transform: statsOpen ? "rotate(0deg)" : "rotate(-90deg)" }} />
                Current Data Status
                {hasData && (
                  <span className="text-xs text-muted-foreground font-normal ml-auto">
                    {totalRows.toLocaleString()} total rows
                  </span>
                )}
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-3">
                {loadingStats ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
                    <Loader2 className="size-4 animate-spin" />
                    Loading stats...
                  </div>
                ) : !hasData ? (
                  <p className="text-sm text-muted-foreground mt-2">
                    No data in database. Click "Generate Data" to create synthetic retail data.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-2">
                    {Object.entries(stats)
                      .filter(([key]) => key !== "_total")
                      .sort(([, a], [, b]) => b - a)
                      .map(([table, count]) => (
                        <div
                          key={table}
                          className="rounded-md border p-3 text-center"
                        >
                          <p className="text-xs text-muted-foreground truncate">
                            {table}
                          </p>
                          <p className="text-lg font-semibold tabular-nums">
                            {count.toLocaleString()}
                          </p>
                        </div>
                      ))}
                    <div className="rounded-md border p-3 text-center bg-teal-50 border-teal-200">
                      <p className="text-xs text-teal-700 font-medium">Total Rows</p>
                      <p className="text-lg font-semibold tabular-nums text-teal-700">
                        {totalRows.toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </CollapsibleContent>
            </Collapsible>
          </CardContent>
        </Card>

        {/* Pipeline Run Management */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ListChecks className="size-4" />
              Pipeline Run Management
            </CardTitle>
            <CardDescription>
              View and manage your pipeline runs
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingRuns ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading runs...
              </div>
            ) : runs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No pipeline runs found.
              </p>
            ) : (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Select Pipeline Runs</Label>
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground underline"
                      onClick={toggleAll}
                    >
                      {selectedRunIds.size === runs.length ? "Deselect all" : "Select all"}
                    </button>
                  </div>
                  <div className="rounded-md border max-h-60 overflow-y-auto divide-y">
                    {runs.map((run) => (
                      <label
                        key={run.id}
                        className="flex items-center gap-3 px-3 py-2 hover:bg-muted/50 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedRunIds.has(run.id)}
                          onChange={() => toggleRunId(run.id)}
                          className="rounded border-gray-300"
                        />
                        <span className="flex-1 truncate">
                          {new Date(run.started_at).toLocaleString()}
                          {run.duration_seconds != null && ` · ${Math.round(run.duration_seconds)}s`}
                        </span>
                        <Badge
                          color={run.status === "completed" ? "green" : run.status === "running" ? "orange" : "red"}
                          className="text-xs shrink-0"
                        >
                          {run.status}
                        </Badge>
                      </label>
                    ))}
                  </div>
                </div>
                {selectedRunIds.size > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedRunIds.size} run{selectedRunIds.size > 1 ? "s" : ""} selected
                  </p>
                )}
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={
                    selectedRunIds.size === 0 ||
                    hasRunningSelected ||
                    deletingRuns ||
                    generating ||
                    updating ||
                    deleting
                  }
                  onClick={() => setShowDeleteRunConfirm(true)}
                >
                  {deletingRuns ? (
                    <>
                      <Loader2 className="size-4 animate-spin mr-2" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="size-4 mr-2" />
                      Delete Selected ({selectedRunIds.size})
                    </>
                  )}
                </Button>
                {hasRunningSelected && (
                  <p className="text-xs text-amber-600">
                    Cannot delete currently running pipelines. Deselect them to proceed.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delete Runs Confirmation Dialog */}
      <AlertDialog open={showDeleteRunConfirm} onOpenChange={setShowDeleteRunConfirm}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {selectedRunIds.size} Pipeline Run{selectedRunIds.size > 1 ? "s" : ""}?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>
                  The following run{selectedRunIds.size > 1 ? "s" : ""} and all associated data
                  will be permanently deleted:
                </p>
                <ul className="rounded-md border divide-y max-h-40 overflow-y-auto text-sm">
                  {runs
                    .filter((r) => selectedRunIds.has(r.id))
                    .map((run) => (
                      <li key={run.id} className="flex items-center justify-between gap-2 px-3 py-2">
                        <span className="truncate">
                          {new Date(run.started_at).toLocaleString()}
                          {run.duration_seconds != null && ` · ${Math.round(run.duration_seconds)}s`}
                        </span>
                        <Badge
                          color={run.status === "completed" ? "green" : run.status === "running" ? "orange" : "red"}
                          className="text-xs shrink-0"
                        >
                          {run.status}
                        </Badge>
                      </li>
                    ))}
                </ul>
                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-foreground">
                    The following data will be permanently removed:
                  </p>
                  <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground pl-1">
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      KPI snapshots
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Forecast snapshots
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Insight snapshots
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Hypothesis snapshots
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      AI analysis
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Cleaned datasets
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Featured datasets
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Cleaning reports
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Feature reports
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="size-1 rounded-full bg-red-400 shrink-0" />
                      Storage artifacts
                    </li>
                  </ul>
                </div>
                <p className="text-xs text-destructive font-medium">
                  This action cannot be undone.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteRuns}
              className="bg-destructive hover:bg-destructive/90 text-white"
            >
              Delete {selectedRunIds.size} Run{selectedRunIds.size > 1 ? "s" : ""}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Generate Confirmation Dialog */}
      <AlertDialog open={showGenerateConfirm} onOpenChange={setShowGenerateConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Generate New Data?</AlertDialogTitle>
            <AlertDialogDescription>
              {hasData
                ? "This will replace all existing raw data with fresh synthetic data. This action cannot be undone."
                : "This will generate 12 synthetic retail datasets in Supabase."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleGenerate}
              className="bg-teal-600 hover:bg-teal-700"
            >
              Generate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete All Data?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete all {totalRows.toLocaleString()} rows of raw data
              from Supabase. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive hover:bg-destructive/90 text-white"
            >
              Delete All Data
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Update Data Modal */}
      <Dialog open={showUpdateModal} onOpenChange={setShowUpdateModal}>
        <DialogContent className="max-w-sm sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Update Data</DialogTitle>
            <DialogDescription>
              Simulate new data being added over a period of time with a specific business scenario.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="update-days">Days to Simulate</Label>
              <Input
                id="update-days"
                type="number"
                value={updateDays}
                onChange={(e) =>
                  setUpdateDays(Math.max(1, Math.min(90, Number(e.target.value) || 1)))
                }
                min={1}
                max={90}
              />
              <p className="text-xs text-muted-foreground">
                Number of days of new data to add (1-90)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="update-scenario">Business Scenario</Label>
              <Select value={updateScenario} onValueChange={setUpdateScenario}>
                <SelectTrigger id="update-scenario">
                  <SelectValue placeholder="Select scenario" />
                </SelectTrigger>
                <SelectContent>
                  {SCENARIOS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {SCENARIOS.find((s) => s.value === updateScenario)?.description}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUpdateModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdate} className="bg-teal-600 hover:bg-teal-700">
              Run Update
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
