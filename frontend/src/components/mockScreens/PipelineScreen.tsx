import { useCallback, useEffect, useRef, useState } from "react";
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
  ChevronDown,
  ChevronRight,
  Eye,
  MessageSquare,
  Zap,
  BarChart3,
  ClipboardList,
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
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function PipelineScreen() {
  const [stages, setStages] = useState<AgentStage[]>(defaultStages);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineDone, setPipelineDone] = useState(false);
  const [totalDuration, setTotalDuration] = useState<number | null>(null);
  const [llmDecisionsLog, setLlmDecisionsLog] = useState<
    { agent: string; decision: string }[]
  >([]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
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

  // Fetch initial status on mount (in case pipeline already ran at startup)
  useEffect(() => {
    apiFetch(`${API_BASE}/api/pipeline/status`)
      .then((r) => r.json())
      .then((data) => {
        if (data.status?.agents) {
          applyCompletedStatus(data.status);
        }
      })
      .catch(() => {});
  }, [applyCompletedStatus]);

  // Start pipeline via SSE stream
  const startPipeline = useCallback(() => {
    setStages(defaultStages.map((s) => ({ ...s })));
    setPipelineRunning(true);
    setPipelineDone(false);
    setTotalDuration(null);
    setLlmDecisionsLog([]);
    setExpandedAgent(null);

    const es = new EventSource(
      `${API_BASE}/api/pipeline/stream?reset=true&alpha=0.05&api_key=${import.meta.env.VITE_API_KEY ?? ""}`
    );
    esRef.current = es;

    es.onmessage = (event) => {
      const data: SSEEvent = JSON.parse(event.data);

      if (data.event === "agent_started") {
        setStages((prev) =>
          prev.map((s) =>
            s.id === data.agent_id
              ? {
                  ...s,
                  status: "running" as const,
                  progress: data.progress_pct || 0,
                  phase: "perceiving",
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
                }
              : s
          )
        );
      }

      if (data.event === "pipeline_complete") {
        setPipelineRunning(false);
        applyCompletedStatus(data);
        es.close();
        esRef.current = null;
      }
    };

    es.onerror = () => {
      setPipelineRunning(false);
      es.close();
      esRef.current = null;
    };
  }, [applyCompletedStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  const completedCount = stages.filter((s) => s.status === "completed").length;
  const overallProgress = Math.round((completedCount / stages.length) * 100);
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

  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case "perceiving":
        return (
          <span className="flex items-center gap-1 text-xs text-purple-600">
            <Eye className="size-3" /> Perceiving environment...
          </span>
        );
      case "reasoning":
        return (
          <span className="flex items-center gap-1 text-xs text-amber-600">
            <Brain className="size-3" /> LLM reasoning...
          </span>
        );
      case "acting":
        return (
          <span className="flex items-center gap-1 text-xs text-blue-600">
            <Zap className="size-3" /> Executing pipeline...
          </span>
        );
      default:
        return null;
    }
  };

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
            <Button
              className="bg-teal-600 hover:bg-teal-700 gap-2"
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
                  ? `Agent ${currentStep} of ${stages.length} is running...`
                  : pipelineDone
                    ? `Completed in ${totalDuration?.toFixed(1)}s`
                    : "Ready to run"}
              </CardDescription>
            </div>
            <Badge
              color={
                pipelineRunning
                  ? "blue"
                  : pipelineDone
                    ? "green"
                    : "gray"
              }
            >
              {pipelineRunning ? (
                <>
                  <Clock className="size-3 mr-1" /> In Progress
                </>
              ) : pipelineDone ? (
                <>
                  <CheckCircle2 className="size-3 mr-1" /> Complete
                </>
              ) : (
                <>
                  <Clock className="size-3 mr-1" /> Idle
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Overall Progress</span>
              <span>
                {completedCount} of {stages.length} agents complete &bull;{" "}
                {overallProgress}%
              </span>
            </div>
            <Progress value={overallProgress} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Pipeline Stages */}
      <div className="space-y-4">
        {stages.map((stage, index) => {
          const isExpanded = expandedAgent === stage.id;
          const hasDecisions =
            stage.llmReasoning || stage.llmDecisions.length > 0;

          return (
            <div key={stage.id}>
              <Card
                className={`border-2 transition-all ${
                  stage.status === "running"
                    ? "border-blue-200 shadow-md"
                    : ""
                }`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    {/* Stage Icon */}
                    <div
                      className={`flex size-14 shrink-0 items-center justify-center rounded-xl ${
                        stage.status === "completed"
                          ? "bg-green-100"
                          : stage.status === "running"
                            ? "bg-blue-100"
                            : stage.status === "error"
                              ? "bg-red-100"
                              : "bg-slate-100"
                      }`}
                    >
                      <stage.icon
                        className={`size-7 ${
                          stage.status === "completed"
                            ? "text-green-600"
                            : stage.status === "running"
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
                            {stage.status}
                          </span>
                        </Badge>
                        {stage.duration !== null && (
                          <span className="text-xs text-muted-foreground">
                            {stage.duration.toFixed(1)}s
                          </span>
                        )}
                      </div>

                      {/* Phase indicator for running agents */}
                      {stage.status === "running" && (
                        <div className="mb-2">
                          {getPhaseLabel(stage.phase)}
                        </div>
                      )}

                      {/* Progress bar for running agents */}
                      {stage.status === "running" && (
                        <div className="space-y-1">
                          <Progress value={stage.progress} className="h-1.5" />
                        </div>
                      )}

                      {/* LLM Reasoning preview */}
                      {stage.llmReasoning && stage.status !== "running" && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                          <Brain className="size-3 inline mr-1 text-amber-500" />
                          {stage.llmReasoning}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {hasDecisions && stage.status !== "running" && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1"
                          onClick={() =>
                            setExpandedAgent(isExpanded ? null : stage.id)
                          }
                        >
                          <MessageSquare className="size-3" />
                          LLM Decisions
                          {isExpanded ? (
                            <ChevronDown className="size-3" />
                          ) : (
                            <ChevronRight className="size-3" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Expanded LLM Decisions */}
                  {isExpanded && hasDecisions && (
                    <div className="mt-4 ml-[72px] rounded-lg border bg-slate-50 p-4">
                      {stage.llmReasoning && (
                        <div className="mb-3">
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                            LLM Reasoning
                          </h4>
                          <p className="text-sm text-slate-700">
                            {stage.llmReasoning}
                          </p>
                        </div>
                      )}
                      {stage.llmDecisions.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                            Decisions Made
                          </h4>
                          <ul className="space-y-1">
                            {stage.llmDecisions.map((d, i) => (
                              <li
                                key={i}
                                className="text-sm text-slate-700 flex items-start gap-2"
                              >
                                <span className="text-amber-500 mt-0.5">
                                  &bull;
                                </span>
                                {d}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Connector Arrow */}
              {index < stages.length - 1 && (
                <div className="flex justify-center py-2">
                  <ArrowDown className="size-5 text-slate-300" />
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
                  className="flex items-start gap-3 rounded-lg border p-3 text-sm"
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
      <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
        <div className="flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-teal-100">
            <Sparkles className="size-4 text-teal-600" />
          </div>
          <div>
            <p className="text-sm font-medium">Multi-Agent Architecture</p>
            <p className="text-xs text-muted-foreground mt-1">
              Each agent autonomously perceives its inputs, reasons about
              strategy using an LLM, and executes the pipeline stage. Agents
              communicate through a shared blackboard &mdash; decisions and
              reasoning are logged for full transparency.
            </p>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
