import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Progress } from "../ui/progress";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
  GitBranch,
  TrendingUp,
  Package,
  ArrowDown,
  Play,
  Brain,
  Eye,
  Zap,
  BarChart3,
  ClipboardList,
  Database,
  Loader2,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface AgentStage {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "error";
  icon: React.ElementType;
  progress: number;
  llmReasoning: string | null;
  llmDecisions: string[];
  duration: number | null;
  phase: string;
  startedAt: number | null;
  activityHints: string[];
}

// Estimated durations (seconds) per agent — used for time display
const ESTIMATED_DURATIONS: Record<string, number> = {
  cleaning: 30,
  features: 25,
  hypothesis: 15,
  insights: 20,
  kpi: 10,
  forecast: 90,
  actions: 15,
};

// Agent descriptions — shown on pending cards in idle state
const AGENT_DESCRIPTIONS: Record<string, string> = {
  cleaning: "Analyzes raw data quality and applies cleaning strategies",
  features: "Analyzes cleaned data structure and engineers features",
  hypothesis: "Runs statistical tests and interprets significant findings",
  insights: "Generates business insights from features and hypothesis results",
  kpi: "Computes and contextualizes key performance indicators",
  forecast: "Trains ML models and generates business forecasts with strategic analysis",
  actions: "Aggregates all upstream data into a prioritized, LLM-generated action plan",
};

// Progress interpolation based on agent phase
function getPhaseProgress(phase: string): number {
  switch (phase) {
    case "perceiving": return 20;
    case "reasoning": return 50;
    case "acting": return 80;
    default: return 0;
  }
}

interface SSEEvent {
  event: string;
  agent_id?: string;
  agent_name?: string;
  step?: number;
  total_steps?: number;
  progress_pct?: number;
  success?: boolean;
  duration?: number;
  llm_reasoning?: string;
  error?: string;
  phase?: string;
  message?: string;
  started_at?: string;
  total_duration_seconds?: number;
  agents?: Record<
    string,
    {
      success: boolean;
      duration_seconds: number;
      llm_reasoning: string | null;
      llm_decisions: string[];
      error: string | null;
    }
  >;
  llm_decisions_log?: { agent: string; decision: string }[];
}

import { API_BASE, apiFetch } from "../../lib/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface PipelineScreenProps {
  onNavigate?: (section: string) => void;
}

// ---------------------------------------------------------------------------
// Default stage definitions (order matches backend agents)
// ---------------------------------------------------------------------------
const defaultStages: AgentStage[] = [
  {
    id: "cleaning",
    name: "Data Cleaning Agent",
    status: "pending",
    icon: Sparkles,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "features",
    name: "Feature Engineering Agent",
    status: "pending",
    icon: GitBranch,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "hypothesis",
    name: "Hypothesis Testing Agent",
    status: "pending",
    icon: BarChart3,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "insights",
    name: "Insights Generation Agent",
    status: "pending",
    icon: Brain,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "kpi",
    name: "KPI Snapshot Agent",
    status: "pending",
    icon: TrendingUp,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "forecast",
    name: "Forecasting Agent",
    status: "pending",
    icon: Package,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
  {
    id: "actions",
    name: "Action Plan Agent",
    status: "pending",
    icon: ClipboardList,
    progress: 0,
    llmReasoning: null,
    llmDecisions: [],
    duration: null,
    phase: "idle",
    startedAt: null,
    activityHints: [],
  },
];

// ---------------------------------------------------------------------------
// Live elapsed timer — counts up every second for running agents
// ---------------------------------------------------------------------------
function LiveTimer({ startedAt, agentId }: { startedAt: number; agentId: string }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, [startedAt]);

  const estimate = ESTIMATED_DURATIONS[agentId];
  return (
    <span className="text-xs text-muted-foreground tabular-nums">
      {elapsed}s{estimate ? ` / ~${estimate}s` : ""}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Pipeline elapsed timer — formats seconds into m:ss or h:mm:ss
// ---------------------------------------------------------------------------
function formatRelativeTime(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return "yesterday";
  return `${Math.floor(diff / 86400)}d ago`;
}

interface LastRunSummary {
  completedAt: string;
  durationSeconds: number;
  successCount: number;
  failedCount: number;
  agentCount: number;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function PipelineElapsedTimer({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(
    Math.floor((Date.now() - startedAt) / 1000),
  );
  useEffect(() => {
    setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <span className="tabular-nums font-medium text-sm">
      {formatElapsed(elapsed)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Phase stepper — shows perceive → reason → act with active indicator
// ---------------------------------------------------------------------------
const PHASES = [
  { key: "perceiving", label: "Perceive", icon: Eye },
  { key: "reasoning", label: "Reason", icon: Brain },
  { key: "acting", label: "Execute", icon: Zap },
] as const;

function PhaseStepper({ currentPhase }: { currentPhase: string }) {
  const phaseIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="flex items-center gap-1.5">
      {PHASES.map((p, i) => {
        const isDone = phaseIndex > i;
        const isActive = phaseIndex === i;
        const Icon = p.icon;
        return (
          <div key={p.key} className="flex items-center gap-1.5">
            {i > 0 && (
              <div
                className={`h-0.5 w-5 rounded-full transition-colors duration-500 ${
                  isDone ? "bg-teal-400" : isActive ? "bg-blue-300" : "bg-slate-200"
                }`}
              />
            )}
            <div
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-all duration-500 ${
                isDone
                  ? "bg-teal-100 text-teal-700"
                  : isActive
                    ? "bg-blue-100 text-blue-700 animate-pulse"
                    : "bg-slate-100 text-slate-400"
              }`}
            >
              {isDone ? (
                <CheckCircle2 className="size-3" />
              ) : (
                <Icon className="size-3" />
              )}
              {p.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animated progress bar — creeps smoothly toward target, never sits still
// ---------------------------------------------------------------------------
function AnimatedProgress({
  target,
  className,
  onDisplayChange,
}: {
  target: number;
  className?: string;
  onDisplayChange?: (value: number) => void;
}) {
  const [display, setDisplay] = useState(target);
  const rafRef = useRef<number>(0);
  const displayRef = useRef(target);
  const targetRef = useRef(target);
  const onDisplayChangeRef = useRef(onDisplayChange);
  onDisplayChangeRef.current = onDisplayChange;

  // Keep targetRef in sync
  useEffect(() => {
    targetRef.current = target;
  }, [target]);

  useEffect(() => {
    let lastTime = performance.now();

    const tick = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;

      const cur = displayRef.current;
      const tgt = targetRef.current;
      let next = cur;

      if (cur < tgt) {
        const speed = Math.max((tgt - cur) * 2.5, 3);
        next = Math.min(cur + speed * dt, tgt);
      } else if (tgt < 100) {
        const ceiling = Math.min(tgt + 15, 99);
        if (cur < ceiling) {
          next = Math.min(cur + 0.8 * dt, ceiling);
        }
      }

      if (next !== cur) {
        displayRef.current = next;
        setDisplay(next);
        onDisplayChangeRef.current?.(next);
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const pct = display;
  // Gradient shifts from blue → teal → green as progress increases
  const hue = 200 + (pct / 100) * 60; // 200 (blue) → 260 is wrong, let's do blue→teal→green
  const gradientFrom = `hsl(${210 - (pct / 100) * 60}, 90%, 55%)`; // 210 (blue) → 150 (teal)
  const gradientTo = `hsl(${210 - (pct / 100) * 80}, 85%, 45%)`; // slightly darker end

  return (
    <div
      className={`relative w-full overflow-hidden rounded-full bg-slate-100 ${className ?? ""}`}
      style={{ height: "10px" }}
    >
      {/* Filled bar with gradient */}
      <div
        className="absolute inset-y-0 left-0 rounded-full"
        style={{
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${gradientFrom}, ${gradientTo})`,
          boxShadow: pct > 0 && pct < 100
            ? `0 0 8px ${gradientFrom}40, 0 0 2px ${gradientFrom}60`
            : undefined,
        }}
      />
      {/* Shimmer overlay while in progress */}
      {pct > 0 && pct < 100 && (
        <div
          className="absolute inset-y-0 left-0 rounded-full overflow-hidden"
          style={{ width: `${pct}%` }}
        >
          <div className="h-full w-full animate-progress-shimmer bg-gradient-to-r from-transparent via-white/30 to-transparent bg-[length:200%_100%]" />
        </div>
      )}
      {/* Glowing leading edge */}
      {pct > 0 && pct < 100 && (
        <div
          className="absolute top-0 bottom-0 w-3 rounded-full animate-pulse"
          style={{
            left: `calc(${pct}% - 6px)`,
            background: `radial-gradient(circle, ${gradientFrom}80, transparent)`,
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Activity ticker — shows recent activity hints from the agent
// ---------------------------------------------------------------------------
function ActivityTicker({ hints }: { hints: string[] }) {
  if (hints.length === 0) return null;
  const recent = hints.slice(-3);
  return (
    <div className="mt-2 space-y-0.5 overflow-hidden max-h-16">
      {recent.map((hint, i) => (
        <p
          key={`${hint}-${i}`}
          className="text-xs text-muted-foreground animate-fade-in-up truncate"
        >
          <span className="text-blue-400 mr-1">&rsaquo;</span>
          {hint}
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Truncated text with inline "see more" / "see less"
// ---------------------------------------------------------------------------
function TruncatedReasoning({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const [isClamped, setIsClamped] = useState(false);
  const textRef = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    const el = textRef.current;
    if (el) setIsClamped(el.scrollHeight > el.clientHeight + 1);
  }, [text]);

  return (
    <div className="mt-1">
      <p
        ref={textRef}
        className={`text-sm text-muted-foreground inline ${!expanded ? "line-clamp-2" : ""}`}
      >
        <Brain className="size-3 inline mr-1 text-amber-500" />
        {text}
        {expanded && isClamped && (
          <>
            {" "}
            <button
              className="text-xs text-teal-600 hover:text-teal-700 font-medium inline"
              onClick={() => setExpanded(false)}
            >
              see less
            </button>
          </>
        )}
      </p>
      {!expanded && isClamped && (
        <button
          className="text-xs text-teal-600 hover:text-teal-700 font-medium"
          onClick={() => setExpanded(true)}
        >
          ...see more
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function PipelineScreen({ onNavigate }: PipelineScreenProps) {
  const [stages, setStages] = useState<AgentStage[]>(defaultStages);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineDone, setPipelineDone] = useState(false);
  const [totalDuration, setTotalDuration] = useState<number | null>(null);
  const [llmDecisionsLog, setLlmDecisionsLog] = useState<
    { agent: string; decision: string }[]
  >([]);
  const [preparingMessage, setPreparingMessage] = useState<string | null>(null);
  const [pipelineStartedAt, setPipelineStartedAt] = useState<number | null>(null);
  const [currentAgentName, setCurrentAgentName] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<LastRunSummary | null>(null);
  const esRef = useRef<EventSource | null>(null);


  // Apply completed pipeline status from API response
  const applyCompletedStatus = useCallback((status: SSEEvent) => {
    if (!status.agents) return;
    setStages((prev) =>
      prev.map((s) => {
        const agentData = status.agents![s.id];
        if (!agentData) return s;
        return {
          ...s,
          status: agentData.success ? "completed" : "error",
          progress: 100,
          llmReasoning: agentData.llm_reasoning,
          llmDecisions: agentData.llm_decisions || [],
          duration: agentData.duration_seconds,
          phase: "idle",
          startedAt: null,
          activityHints: [],
        };
      })
    );
    if (status.llm_decisions_log) {
      setLlmDecisionsLog(status.llm_decisions_log);
    }
    if (status.total_duration_seconds) {
      setTotalDuration(status.total_duration_seconds);
    }
    setPipelineDone(true);
  }, []);

  // Shared SSE event handler used by both startPipeline and reconnect
  const handleSSEEvent = useCallback(
    (data: SSEEvent) => {
      if (data.event === "pipeline_started" && data.started_at) {
        setPipelineStartedAt(new Date(data.started_at).getTime());
      }

      if (data.event === "pipeline_preparing") {
        setPreparingMessage(data.message || "Preparing pipeline...");
      }

      if (data.event === "agent_started") {
        setPreparingMessage(null);
        setCurrentAgentName(data.agent_name || null);
        setStages((prev) =>
          prev.map((s) =>
            s.id === data.agent_id
              ? {
                  ...s,
                  status: "running" as const,
                  progress: getPhaseProgress("perceiving"),
                  phase: "perceiving",
                  startedAt: Date.now(),
                  activityHints: [],
                }
              : s
          )
        );
      }

      if (data.event === "agent_phase_changed" && data.agent_id && data.phase) {
        setStages((prev) =>
          prev.map((s) =>
            s.id === data.agent_id && s.status === "running"
              ? {
                  ...s,
                  phase: data.phase!,
                  progress: getPhaseProgress(data.phase!),
                }
              : s
          )
        );
      }

      if (data.event === "agent_activity_hint" && data.agent_id && data.message) {
        setStages((prev) =>
          prev.map((s) =>
            s.id === data.agent_id && s.status === "running"
              ? {
                  ...s,
                  activityHints: [...s.activityHints.slice(-4), data.message!],
                }
              : s
          )
        );
      }

      if (data.event === "agent_completed") {
        setStages((prev) =>
          prev.map((s) =>
            s.id === data.agent_id
              ? {
                  ...s,
                  status: data.success
                    ? ("completed" as const)
                    : ("error" as const),
                  progress: 100,
                  llmReasoning: data.llm_reasoning || null,
                  duration: data.duration || null,
                  phase: "idle",
                  startedAt: null,
                  activityHints: [],
                }
              : s
          )
        );
      }

      if (data.event === "pipeline_complete") {
        setPipelineRunning(false);
        setPreparingMessage(null);
        setPipelineStartedAt(null);
        setCurrentAgentName(null);
        applyCompletedStatus(data);
        esRef.current?.close();
        esRef.current = null;
      }

    },
    [applyCompletedStatus]
  );

  // Connect to the subscribe-only SSE stream (for reconnecting to a running pipeline)
  const connectToSubscribeStream = useCallback(() => {
    const es = new EventSource(
      `${API_BASE}/api/pipeline/stream/subscribe?api_key=${import.meta.env.VITE_API_KEY ?? ""}`
    );
    esRef.current = es;

    es.onmessage = (event) => {
      const data: SSEEvent = JSON.parse(event.data);
      handleSSEEvent(data);
    };

    es.onerror = () => {
      // Don't set pipelineRunning=false here — the polling fallback
      // will read from DB and determine the actual state
      es.close();
      esRef.current = null;
    };
  }, [handleSSEEvent]);

  // Fetch initial status on mount — handles both completed and running pipelines
  useEffect(() => {
    apiFetch(`${API_BASE}/api/pipeline/status`)
      .then((r) => r.json())
      .then((data) => {
        if (data.running) {
          // Pipeline is currently running — restore partial state and reconnect
          setPipelineRunning(true);
          setPipelineDone(false);

          // Restore pipeline start time from DB
          if (data.started_at) {
            setPipelineStartedAt(new Date(data.started_at).getTime());
          }

          // Restore current agent name from stage definitions
          if (data.current_agent) {
            const stage = defaultStages.find((s) => s.id === data.current_agent);
            setCurrentAgentName(stage?.name || null);
          }

          // Apply completed agents from partial progress
          if (data.partial && Object.keys(data.partial).length > 0) {
            setStages((prev) =>
              prev.map((s) => {
                const evt = data.partial[s.id];
                if (!evt) return s;
                return {
                  ...s,
                  status: evt.success
                    ? ("completed" as const)
                    : ("error" as const),
                  progress: 100,
                  llmReasoning: evt.llm_reasoning || null,
                  duration: evt.duration || null,
                  phase: "idle",
                  startedAt: null,
                  activityHints: [],
                };
              })
            );
          }

          // Mark current agent as running
          if (data.current_agent) {
            setStages((prev) =>
              prev.map((s) =>
                s.id === data.current_agent
                  ? {
                      ...s,
                      status: "running" as const,
                      progress: getPhaseProgress("perceiving"),
                      phase: "perceiving",
                      startedAt: Date.now(),
                      activityHints: [],
                    }
                  : s
              )
            );
          }

          // Reconnect to SSE stream for remaining events
          connectToSubscribeStream();
        } else if (data.status?.agents) {
          // Pipeline already completed — show results
          applyCompletedStatus(data.status);
          // Extract last-run summary for idle state display
          const agents = data.status.agents as Record<string, { success: boolean }>;
          const entries = Object.values(agents);
          setLastRun({
            completedAt: data.status.completed_at ?? new Date().toISOString(),
            durationSeconds: data.status.total_duration_seconds ?? 0,
            successCount: entries.filter((a) => a.success).length,
            failedCount: entries.filter((a) => !a.success).length,
            agentCount: entries.length,
          });
        }
      })
      .catch(() => {});
  }, [applyCompletedStatus, connectToSubscribeStream]);

  // Start pipeline via SSE stream
  const startPipeline = useCallback(() => {
    setStages(defaultStages.map((s) => ({ ...s })));
    setPipelineRunning(true);
    setPipelineDone(false);
    setTotalDuration(null);
    setLlmDecisionsLog([]);
    setPreparingMessage("Initializing pipeline...");
    setPipelineStartedAt(Date.now());
    setCurrentAgentName(null);

    const es = new EventSource(
      `${API_BASE}/api/pipeline/stream?reset=true&alpha=0.05&api_key=${import.meta.env.VITE_API_KEY ?? ""}`
    );
    esRef.current = es;

    es.onmessage = (event) => {
      const data: SSEEvent = JSON.parse(event.data);
      handleSSEEvent(data);
    };

    es.onerror = () => {
      // Don't set pipelineRunning=false here — the polling fallback
      // will read from DB and determine the actual state
      es.close();
      esRef.current = null;
    };
  }, [handleSSEEvent]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  // Polling fallback: if pipeline is running but SSE is down, poll DB for progress.
  useEffect(() => {
    if (!pipelineRunning) return;
    const interval = setInterval(async () => {
      // Only poll if SSE is not connected
      if (esRef.current?.readyState === EventSource.OPEN) return;
      try {
        const r = await apiFetch(`${API_BASE}/api/pipeline/status`);
        const data = await r.json();
        if (data.partial) {
          setStages((prev) =>
            prev.map((s) => {
              const evt = data.partial[s.id];
              if (!evt) return s;
              return {
                ...s,
                status: evt.success
                  ? ("completed" as const)
                  : ("error" as const),
                progress: 100,
                llmReasoning: evt.llm_reasoning || null,
                duration: evt.duration || null,
                phase: "idle",
                startedAt: null,
                activityHints: [],
              };
            })
          );
        }
        if (data.current_agent) {
          setStages((prev) =>
            prev.map((s) =>
              s.id === data.current_agent && s.status !== "completed" && s.status !== "error"
                ? {
                    ...s,
                    status: "running" as const,
                    progress: getPhaseProgress("perceiving"),
                    phase: "perceiving",
                    startedAt: s.startedAt ?? Date.now(),
                    activityHints: s.activityHints ?? [],
                  }
                : s
            )
          );
        }
        if (!data.running) {
          setPipelineRunning(false);
          setPipelineDone(true);
          clearInterval(interval);
        }
      } catch {
        // Ignore polling errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [pipelineRunning]);

  const completedCount = stages.filter((s) => s.status === "completed").length;
  const runningStage = stages.find((s) => s.status === "running");
  // Granular overall progress: completed agents + fraction of running agent
  const overallTarget = Math.round(
    ((completedCount + (runningStage ? runningStage.progress / 100 : 0)) /
      stages.length) *
      100,
  );
  const [displayedOverallPct, setDisplayedOverallPct] = useState(0);
  const currentStep =
    stages.findIndex((s) => s.status === "running") + 1 || completedCount;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "green";
      case "running":
        return "blue";
      case "error":
        return "red";
      default:
        return "gray";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="size-5 text-green-600" />;
      case "running":
        return <Clock className="size-5 text-blue-600 animate-spin" />;
      case "error":
        return <AlertCircle className="size-5 text-red-600" />;
      default:
        return <Clock className="size-5 text-slate-400" />;
    }
  };

  // getPhaseLabel removed — replaced by PhaseStepper component

  return (
    <div>
      {/* Header with Controls */}
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">
              Multi-Agent Pipeline
            </h1>
            <p className="text-xs text-muted-foreground">
              7 autonomous agents with LLM-driven perceive &rarr; reason &rarr;
              act cycles
            </p>
          </div>
          <div className="flex items-center gap-3">
            {pipelineDone && onNavigate && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => onNavigate("customer-insights")}
              >
                <Eye className="size-4" />
                View Insights
              </Button>
            )}
            <Button
              className={`bg-teal-600 hover:bg-teal-700 gap-2 ${!pipelineRunning && !pipelineDone ? "shadow-lg shadow-teal-200" : ""}`}
              onClick={startPipeline}
              disabled={pipelineRunning}
            >
              <Play className="size-4" />
              {pipelineRunning ? "Running..." : "Run Pipeline"}
            </Button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Pipeline Status</CardTitle>
              <CardDescription>
                {pipelineRunning
                  ? currentAgentName
                    ? `${currentAgentName} is running... (step ${currentStep} of ${stages.length})`
                    : `Preparing pipeline...`
                  : pipelineDone
                    ? `Completed in ${totalDuration?.toFixed(1)}s`
                    : "7 AI agents ready to analyze your data"}
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              {/* Elapsed timer */}
              {pipelineRunning && pipelineStartedAt && (
                <div className="flex items-center gap-1.5 rounded-md bg-blue-50 px-2.5 py-1">
                  <Clock className="size-3.5 text-blue-500" />
                  <PipelineElapsedTimer startedAt={pipelineStartedAt} />
                </div>
              )}
              <Badge
                color={
                  pipelineRunning
                    ? "blue"
                    : pipelineDone
                      ? "green"
                      : "teal"
                }
              >
                {pipelineRunning ? (
                  <>
                    <Loader2 className="size-3 mr-1 animate-spin" /> In Progress
                  </>
                ) : pipelineDone ? (
                  <>
                    <CheckCircle2 className="size-3 mr-1" /> Complete
                  </>
                ) : (
                  <>
                    <Play className="size-3 mr-1" /> Ready
                  </>
                )}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {pipelineRunning ? (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="tabular-nums font-medium">
                  {completedCount} of {stages.length} agents &bull;{" "}
                  {Math.round(displayedOverallPct)}%
                </span>
              </div>
              <AnimatedProgress
                target={overallTarget}
                onDisplayChange={setDisplayedOverallPct}
              />
            </div>
          ) : pipelineDone ? (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Overall Progress</span>
                <span className="tabular-nums font-medium">
                  {completedCount} of {stages.length} agents &bull; 100%
                </span>
              </div>
              <Progress value={100} className="h-2" />
            </div>
          ) : (
            /* Idle state */
            <div className="space-y-3">
              {lastRun ? (
                <div className="flex items-center gap-3 text-sm text-muted-foreground rounded-md bg-slate-50 px-3 py-2.5">
                  <CheckCircle2 className="size-4 text-green-500 shrink-0" />
                  <span>
                    Last run: {formatRelativeTime(lastRun.completedAt)}
                    {" · "}
                    {formatElapsed(Math.round(lastRun.durationSeconds))}
                    {" · "}
                    {lastRun.successCount}/{lastRun.agentCount} agents succeeded
                  </span>
                  {lastRun.failedCount > 0 && (
                    <Badge color="red" className="ml-auto">
                      {lastRun.failedCount} failed
                    </Badge>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Click <span className="font-medium text-teal-600">Run Pipeline</span> to
                  start the multi-agent analysis. Typically takes ~3 minutes.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Data preparation banner — shown before first agent starts */}
      {preparingMessage && (
        <Card className="border-2 border-amber-200 agent-card-active">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-amber-100 animate-pulse">
                <Database className="size-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium">Preparing Data</h3>
                  <Loader2 className="size-3.5 text-amber-600 animate-spin" />
                </div>
                <p className="text-xs text-muted-foreground animate-fade-in-up">
                  {preparingMessage}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pipeline Stages */}
      <div className="space-y-4">
        {stages.map((stage, index) => {
          const isRunning = stage.status === "running";
          const prevCompleted =
            index > 0 &&
            stages[index - 1].status === "completed" &&
            isRunning;
          return (
            <div key={stage.id}>
              <Card
                className={`border-2 transition-all duration-500 ${
                  isRunning
                    ? "border-blue-200 shadow-md agent-card-active"
                    : ""
                }`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    {/* Stage Icon */}
                    <div
                      className={`flex size-14 shrink-0 items-center justify-center rounded-md transition-colors duration-500 ${
                        stage.status === "completed"
                          ? "bg-green-100"
                          : isRunning
                            ? "bg-blue-100 animate-pulse"
                            : stage.status === "error"
                              ? "bg-red-100"
                              : "bg-slate-100"
                      }`}
                    >
                      <stage.icon
                        className={`size-7 ${
                          stage.status === "completed"
                            ? "text-green-600"
                            : isRunning
                              ? "text-blue-600"
                              : stage.status === "error"
                                ? "text-red-600"
                                : "text-slate-400"
                        }`}
                      />
                    </div>

                    {/* Stage Details */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-base font-medium">{stage.name}</h3>
                        <Badge
                          color={getStatusColor(stage.status)}
                        >
                          {getStatusIcon(stage.status)}
                          <span className="ml-1 capitalize">
                            {stage.status === "pending" && !pipelineRunning ? "Ready" : stage.status}
                          </span>
                        </Badge>
                        {/* Live timer for running agents */}
                        {isRunning && stage.startedAt && (
                          <LiveTimer startedAt={stage.startedAt} agentId={stage.id} />
                        )}
                        {/* Static duration for completed agents */}
                        {!isRunning && stage.duration !== null && (
                          <span className="text-xs text-muted-foreground">
                            {stage.duration.toFixed(1)}s
                          </span>
                        )}
                      </div>

                      {/* Phase stepper for running agents */}
                      {isRunning && (
                        <div className="mb-2">
                          <PhaseStepper currentPhase={stage.phase} />
                        </div>
                      )}

                      {/* Progress bar for running agents */}
                      {isRunning && (
                        <div className="space-y-1">
                          <AnimatedProgress
                            target={stage.progress}
                            className="h-1.5"
                          />
                        </div>
                      )}

                      {/* Activity ticker for running agents */}
                      {isRunning && <ActivityTicker hints={stage.activityHints} />}

                      {/* Description for pending agents in idle state */}
                      {stage.status === "pending" && !pipelineRunning && (
                        <p className="text-sm text-muted-foreground">
                          {AGENT_DESCRIPTIONS[stage.id]}
                        </p>
                      )}

                      {/* LLM Reasoning with see more/less */}
                      {stage.llmReasoning && !isRunning && (
                        <TruncatedReasoning text={stage.llmReasoning} />
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Connector Arrow — animated when data flows from completed to running */}
              {index < stages.length - 1 && (
                <div className="flex justify-center py-2">
                  <ArrowDown
                    className={`size-5 transition-colors duration-300 ${
                      prevCompleted
                        ? "text-blue-400 animate-flow-down"
                        : "text-slate-300"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* LLM Decisions Log (shown after pipeline completes) */}
      {pipelineDone && llmDecisionsLog.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="size-5 text-amber-500" />
              Agent Decision Transparency Log
            </CardTitle>
            <CardDescription>
              All LLM-driven decisions made during pipeline execution (
              {llmDecisionsLog.length} decisions across{" "}
              {stages.filter((s) => s.status === "completed").length} agents)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {llmDecisionsLog.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-md border p-3 text-sm"
                >
                  <Badge variant="outline" className="shrink-0 text-xs">
                    {entry.agent.replace(" Agent", "")}
                  </Badge>
                  <span className="text-slate-700">{entry.decision}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pipeline Info */}
      <div className="rounded-md border border-teal-200 bg-teal-50 p-4">
        <div className="flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-teal-100">
            <Sparkles className="size-4 text-teal-600" />
          </div>
          <div>
            <p className="text-sm font-medium">
              {!pipelineRunning && !pipelineDone ? "How it works" : "Multi-Agent Architecture"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Each agent autonomously perceives its inputs, reasons about
              strategy using an LLM, and executes the pipeline stage. Agents
              communicate through a shared blackboard &mdash; decisions and
              reasoning are logged for full transparency.
              {!pipelineRunning && !pipelineDone && " The full pipeline typically runs in ~3 minutes."}
            </p>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
