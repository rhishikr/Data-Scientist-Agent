-- Add current_agent column to pipeline_runs for tracking in-progress agent
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS current_agent TEXT DEFAULT NULL;
