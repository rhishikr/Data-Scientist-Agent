-- Disable Row Level Security on all pipeline tables.
-- This allows the anon key to read/write freely.
-- For a production app you'd use the service_role key instead,
-- but for a capstone demo this is fine.

ALTER TABLE pipeline_runs      DISABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_snapshots      DISABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_snapshots DISABLE ROW LEVEL SECURITY;
ALTER TABLE insight_snapshots  DISABLE ROW LEVEL SECURITY;
ALTER TABLE hypothesis_snapshots DISABLE ROW LEVEL SECURITY;
ALTER TABLE cleaned_datasets   DISABLE ROW LEVEL SECURITY;
ALTER TABLE featured_datasets  DISABLE ROW LEVEL SECURITY;
ALTER TABLE cleaning_reports   DISABLE ROW LEVEL SECURITY;
ALTER TABLE feature_reports    DISABLE ROW LEVEL SECURITY;
