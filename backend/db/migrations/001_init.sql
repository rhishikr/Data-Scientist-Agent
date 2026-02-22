-- ============================================================================
-- Data Scientist Agent — Supabase Schema Migration
-- ============================================================================

-- 1. pipeline_runs — tracks each pipeline execution
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  duration_seconds FLOAT,
  agent_summary JSONB,
  llm_decisions_log JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. kpi_snapshots
CREATE TABLE IF NOT EXISTS kpi_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. forecast_snapshots
CREATE TABLE IF NOT EXISTS forecast_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. insight_snapshots
CREATE TABLE IF NOT EXISTS insight_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. hypothesis_snapshots
CREATE TABLE IF NOT EXISTS hypothesis_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. cleaned_datasets — metadata + preview per cleaned table
CREATE TABLE IF NOT EXISTS cleaned_datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  table_name TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  column_count INTEGER NOT NULL,
  preview_rows JSONB NOT NULL,
  column_stats JSONB NOT NULL,
  storage_path TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. featured_datasets — metadata + preview per featured table
CREATE TABLE IF NOT EXISTS featured_datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  table_name TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  column_count INTEGER NOT NULL,
  preview_rows JSONB NOT NULL,
  column_stats JSONB NOT NULL,
  storage_path TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. cleaning_reports
CREATE TABLE IF NOT EXISTS cleaning_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  report JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 9. feature_reports
CREATE TABLE IF NOT EXISTS feature_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  report JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast lookups by run_id
CREATE INDEX IF NOT EXISTS idx_kpi_snapshots_run_id ON kpi_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_forecast_snapshots_run_id ON forecast_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_insight_snapshots_run_id ON insight_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_hypothesis_snapshots_run_id ON hypothesis_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_cleaned_datasets_run_id ON cleaned_datasets(run_id);
CREATE INDEX IF NOT EXISTS idx_featured_datasets_run_id ON featured_datasets(run_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_reports_run_id ON cleaning_reports(run_id);
CREATE INDEX IF NOT EXISTS idx_feature_reports_run_id ON feature_reports(run_id);

-- Storage bucket (must be created via Supabase dashboard or API, not SQL)
-- Bucket name: pipeline-artifacts
-- Structure: runs/<run_id>/cleaned/<table>.csv
--            runs/<run_id>/featured/<table>.csv
