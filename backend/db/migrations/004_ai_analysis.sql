-- ============================================================================
-- AI Analysis Snapshots — stores cached LLM-generated analysis per run
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_analysis_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_analysis_run_id ON ai_analysis_snapshots(run_id);
