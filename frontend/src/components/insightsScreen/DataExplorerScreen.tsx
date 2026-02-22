import { useState, useMemo } from "react";
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  Database,
  Download,
  Layers,
  FileSpreadsheet,
  ArrowRight,
} from "lucide-react";

import { RunSelector } from "./RunSelector";
import {
  useCleanedData,
  useFeaturedData,
  type DatasetPreview,
} from "./dashboard/data";

function SummaryCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: any;
}) {
  return (
    <Card>
      <CardContent className="p-4 flex items-center gap-3">
        <div className="rounded-lg bg-teal-50 p-2">
          <Icon className="size-5 text-teal-600" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function DataPreviewTable({
  dataset,
}: {
  dataset: DatasetPreview;
}) {
  const columns = useMemo(() => {
    if (!dataset.preview_rows.length) return [];
    return Object.keys(dataset.preview_rows[0]);
  }, [dataset.preview_rows]);

  const displayRows = dataset.preview_rows.slice(0, 50);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {dataset.row_count.toLocaleString()} rows
          </Badge>
          <Badge variant="outline">{dataset.column_count} columns</Badge>
        </div>
        {dataset.download_url && (
          <Button variant="outline" size="sm" asChild>
            <a
              href={dataset.download_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download className="size-4 mr-2" />
              Download Full CSV
            </a>
          </Button>
        )}
      </div>

      <div className="rounded-md border overflow-x-auto max-h-[400px] overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col} className="text-xs">
                  {col}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayRows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((col) => (
                  <TableCell key={col} className="text-xs">
                    {row[col] == null ? (
                      <span className="text-muted-foreground italic">null</span>
                    ) : (
                      String(row[col])
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {displayRows.length < dataset.preview_rows.length && (
        <p className="text-xs text-muted-foreground text-center">
          Showing {displayRows.length} of {dataset.preview_rows.length} preview
          rows ({dataset.row_count.toLocaleString()} total in full dataset)
        </p>
      )}
    </div>
  );
}

function ColumnStatsPanel({ stats }: { stats: Record<string, any> }) {
  const entries = Object.entries(stats);
  if (!entries.length) return null;

  return (
    <div className="rounded-md border overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Column</TableHead>
            <TableHead className="text-xs">Type</TableHead>
            <TableHead className="text-xs">Nulls</TableHead>
            <TableHead className="text-xs">Unique</TableHead>
            <TableHead className="text-xs">Samples</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([col, info]) => (
            <TableRow key={col}>
              <TableCell className="text-xs font-mono">{col}</TableCell>
              <TableCell className="text-xs">
                <Badge variant="outline" className="text-xs">
                  {info.dtype}
                </Badge>
              </TableCell>
              <TableCell className="text-xs">{info.null_count}</TableCell>
              <TableCell className="text-xs">{info.unique_count}</TableCell>
              <TableCell className="text-xs max-w-[200px] truncate">
                {(info.sample_values || []).slice(0, 3).join(", ")}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function DataStageSection({
  title,
  icon: Icon,
  tables,
  report,
  loading,
}: {
  title: string;
  icon: any;
  tables: DatasetPreview[];
  report: Record<string, any>;
  loading: boolean;
}) {
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [showStats, setShowStats] = useState(false);

  const tableNames = useMemo(() => tables.map((t) => t.table_name), [tables]);
  const activeTable = useMemo(
    () =>
      tables.find((t) => t.table_name === selectedTable) || tables[0] || null,
    [tables, selectedTable]
  );

  const totalRows = useMemo(
    () => tables.reduce((sum, t) => sum + t.row_count, 0),
    [tables]
  );

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Loading {title.toLowerCase()} data...
        </CardContent>
      </Card>
    );
  }

  if (!tables.length) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          No {title.toLowerCase()} data available for this run.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-teal-100 p-2">
          <Icon className="size-5 text-teal-700" />
        </div>
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>

      <div className="grid gap-3 grid-cols-3">
        <SummaryCard
          label="Tables"
          value={tables.length}
          icon={FileSpreadsheet}
        />
        <SummaryCard
          label="Total Rows"
          value={totalRows.toLocaleString()}
          icon={Database}
        />
        <SummaryCard
          label="Avg Columns"
          value={
            tables.length
              ? Math.round(
                  tables.reduce((s, t) => s + t.column_count, 0) / tables.length
                )
              : 0
          }
          icon={Layers}
        />
      </div>

      <div className="flex items-center gap-3">
        <Select
          value={activeTable?.table_name ?? ""}
          onValueChange={(v) => setSelectedTable(v)}
        >
          <SelectTrigger className="w-[260px]">
            <SelectValue placeholder="Select table" />
          </SelectTrigger>
          <SelectContent>
            {tableNames.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowStats(!showStats)}
        >
          {showStats ? "Hide Column Stats" : "Show Column Stats"}
        </Button>
      </div>

      {activeTable && <DataPreviewTable dataset={activeTable} />}

      {showStats && activeTable && (
        <ColumnStatsPanel stats={activeTable.column_stats} />
      )}
    </div>
  );
}

export function DataExplorerScreen() {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: cleanedData, loading: cleanedLoading } =
    useCleanedData(selectedRunId);
  const { data: featuredData, loading: featuredLoading } =
    useFeaturedData(selectedRunId);

  return (
    <div>
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Data Explorer</h1>
            <p className="text-xs text-muted-foreground">
              Explore cleaned and engineered datasets from each pipeline run
            </p>
          </div>
          <RunSelector
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
          />
        </div>
      </div>

      <div className="p-6 space-y-8">
      <DataStageSection
        title="Cleaned Data"
        icon={Database}
        tables={cleanedData?.tables ?? []}
        report={cleanedData?.report ?? {}}
        loading={cleanedLoading}
      />

      <div className="flex items-center justify-center text-muted-foreground">
        <ArrowRight className="size-5" />
      </div>

      <DataStageSection
        title="Feature Engineered Data"
        icon={Layers}
        tables={featuredData?.tables ?? []}
        report={featuredData?.report ?? {}}
        loading={featuredLoading}
      />
      </div>
    </div>
  );
}
