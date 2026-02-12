import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Progress } from "../ui/progress";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  Database,
  Sparkles,
  GitBranch,
  TrendingUp,
  Users,
  Package,
  ArrowRight,
} from "lucide-react";

export function PipelineScreen() {
  const pipelineStages = [
    {
      id: 1,
      name: "Data Upload & Schema Check",
      status: "completed",
      icon: Database,
      metrics: ["3 sources connected", "52,101 total rows"],
      progress: 100,
    },
    {
      id: 2,
      name: "Cleaning & Validation",
      status: "completed",
      icon: Sparkles,
      metrics: ["95% rows retained", "187 duplicates removed"],
      progress: 100,
    },
    {
      id: 3,
      name: "Feature Engineering & Hypothesis Testing",
      status: "running",
      icon: GitBranch,
      metrics: ["12 features generated", "Running tests..."],
      progress: 65,
    },
    {
      id: 4,
      name: "Modeling & Prediction",
      status: "pending",
      icon: TrendingUp,
      metrics: ["Pending", "Model: XGBoost"],
      progress: 0,
    },
    {
      id: 5,
      name: "Customer Insights",
      status: "pending",
      icon: Users,
      metrics: ["Pending", "Segmentation ready"],
      progress: 0,
    },
    {
      id: 6,
      name: "Inventory & Sales Forecasts",
      status: "pending",
      icon: Package,
      metrics: ["Pending", "30-day forecast"],
      progress: 0,
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600 bg-green-50 border-green-200";
      case "running":
        return "text-blue-600 bg-blue-50 border-blue-200";
      case "error":
        return "text-red-600 bg-red-50 border-red-200";
      default:
        return "text-slate-600 bg-slate-50 border-slate-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="size-5 text-green-600" />;
      case "running":
        return <Clock className="size-5 text-blue-600" />;
      case "error":
        return <AlertCircle className="size-5 text-red-600" />;
      default:
        return <Clock className="size-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="mb-2">Pipeline Orchestration</h1>
          <p className="text-muted-foreground">
            Automated end-to-end analytics workflow
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select defaultValue="demo">
            <SelectTrigger className="w-[240px]">
              <SelectValue placeholder="Select dataset" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="demo">UCI Online Shoppers</SelectItem>
              <SelectItem value="march">Transactions – March 2025</SelectItem>
              <SelectItem value="q1">Q1 2025 Complete</SelectItem>
            </SelectContent>
          </Select>
          <Select defaultValue="combined">
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Use case" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="customer">Customer Analytics</SelectItem>
              <SelectItem value="inventory">Inventory Analytics</SelectItem>
              <SelectItem value="combined">Combined</SelectItem>
            </SelectContent>
          </Select>
          <Button className="bg-teal-600 hover:bg-teal-700">
            Run Pipeline
          </Button>
        </div>
      </div>

      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Pipeline Status</CardTitle>
              <CardDescription>
                Current run started 47 minutes ago
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-blue-600 border-blue-200">
              <Clock className="size-3 mr-1" />
              In Progress
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Overall Progress</span>
              <span>Stage 3 of 6 • 45% Complete</span>
            </div>
            <Progress value={45} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Pipeline Stages */}
      <div className="space-y-4">
        {pipelineStages.map((stage, index) => (
          <div key={stage.id}>
            <Card
              className={`border-2 ${stage.status === "running" ? "border-blue-200 shadow-md" : ""}`}
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
                          : "bg-slate-100"
                    }`}
                  >
                    <stage.icon
                      className={`size-7 ${
                        stage.status === "completed"
                          ? "text-green-600"
                          : stage.status === "running"
                            ? "text-blue-600"
                            : "text-slate-400"
                      }`}
                    />
                  </div>

                  {/* Stage Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base">{stage.name}</h3>
                      <Badge
                        variant="outline"
                        className={getStatusColor(stage.status)}
                      >
                        {getStatusIcon(stage.status)}
                        <span className="ml-1 capitalize">{stage.status}</span>
                      </Badge>
                    </div>

                    <div className="flex gap-6 mb-3">
                      {stage.metrics.map((metric, i) => (
                        <p key={i} className="text-sm text-muted-foreground">
                          {metric}
                        </p>
                      ))}
                    </div>

                    {stage.status === "running" && (
                      <div className="space-y-1">
                        <Progress value={stage.progress} className="h-1.5" />
                        <p className="text-xs text-muted-foreground">
                          {stage.progress}% complete
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {stage.status === "completed" && (
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    )}
                    {stage.status === "running" && (
                      <Button variant="outline" size="sm">
                        View Logs
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Connector Arrow */}
            {index < pipelineStages.length - 1 && (
              <div className="flex justify-center py-2">
                <ArrowRight className="size-5 text-slate-300" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pipeline Info */}
      <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
        <div className="flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-teal-100">
            <Sparkles className="size-4 text-teal-600" />
          </div>
          <div>
            <p className="text-sm">
              This pipeline runs automatically once data is connected
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              You can monitor progress in real-time and review detailed logs for
              each stage. When complete, insights will be available in Customer
              Insights and Inventory & Sales sections.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
