import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Badge } from "../ui/badge";
import { useRuns, type PipelineRun } from "./dashboard/data";

type Props = {
  selectedRunId: string | null;
  onSelectRun: (runId: string | null) => void;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RunSelector({ selectedRunId, onSelectRun }: Props) {
  const { runs, loading } = useRuns();

  const runOptions = useMemo(() => {
    return runs.map((run, i) => ({
      ...run,
      label: `Run ${formatDate(run.started_at)}${i === 0 ? " (latest)" : ""}`,
    }));
  }, [runs]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        Loading runs...
      </div>
    );
  }

  if (runOptions.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No pipeline runs yet. Run the pipeline first.
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-muted-foreground">
        Pipeline Run:
      </span>
      <Select
        value={selectedRunId ?? "latest"}
        onValueChange={(v) => onSelectRun(v === "latest" ? null : v)}
      >
        <SelectTrigger className="w-[320px]">
          <SelectValue placeholder="Select a run" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="latest">Latest Run</SelectItem>
          {runOptions.map((run) => (
            <SelectItem key={run.id} value={run.id}>
              <div className="flex items-center gap-2">
                <span>{run.label}</span>
                <Badge
                  variant={run.status === "completed" ? "default" : "destructive"}
                  className="text-xs"
                >
                  {run.status}
                </Badge>
                {run.duration_seconds != null && (
                  <span className="text-xs text-muted-foreground">
                    {run.duration_seconds.toFixed(1)}s
                  </span>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
