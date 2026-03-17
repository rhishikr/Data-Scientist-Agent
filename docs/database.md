# Database & Storage

This document explains the database schema, migrations, and storage layer used by the Data Scientist Agent.

## Overview

The project uses **Supabase** as its database — a managed PostgreSQL service with:
- **PostgreSQL tables** for structured data (pipeline runs, snapshots, chat history)
- **pgvector extension** for embedding-based similarity search (RAG)
- **Storage buckets** for file artifacts (CSV files from pipeline runs)

There is no local database. All persistence goes through Supabase.

## Database Access Layer

### `backend/db/supabase_client.py`

Singleton Supabase client with retry logic:

- `get_supabase()` — Returns a Supabase client instance (creates on first call)
- `reset_client()` — Forces a fresh client on next call (used after connection errors)
- `with_retry(fn, retries=2)` — Retries transient errors (`ReadError`, socket `10035`)

Requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` environment variables.

### `backend/db/store.py`

All CRUD functions for pipeline data (~600 lines). Key functions:

**Pipeline Runs:**
- `create_pipeline_run()` → returns `run_id`
- `complete_pipeline_run(run_id, status, duration, agent_summary, llm_decisions_log)`
- `get_pipeline_runs()` → list of all runs
- `get_running_pipeline()` → currently running pipeline (if any)
- `delete_pipeline_run(run_id)` → delete run and all associated snapshots

**Snapshot Storage:**
- `store_kpi_snapshot(run_id, data)`, `get_latest_kpi_snapshot()`, `get_run_kpi_snapshot(run_id)`
- `store_forecast_snapshot(...)`, `get_latest_forecast_snapshot()`, `get_run_forecast_snapshot(...)`
- `store_insight_snapshot(...)`, `get_latest_insight_snapshot()`, `get_run_insight_snapshot(...)`
- `store_hypothesis_snapshot(...)`, `get_latest_hypothesis_snapshot()`, `get_run_hypothesis_snapshot(...)`
- `store_ai_analysis(...)`, `store_comparison_ai(...)` — LLM-generated analysis caching

**Data Artifacts:**
- `store_cleaned_dataset(run_id, table_name, df)` — Upload cleaned DataFrame
- `store_featured_dataset(run_id, table_name, df)` — Upload feature-engineered DataFrame
- `get_cleaned_datasets(run_id)` → preview with column stats
- `get_featured_datasets(run_id)` → preview with column stats
- `get_signed_url(path)` → temporary download URL for CSV files in storage bucket

**Prescription Tracking:**
- `upsert_prescription_status(prescription_id, status)`
- `get_prescription_statuses(run_id)`

### `backend/db/raw_store.py`

Raw data management (~300 lines):

- `upload_raw_table(table_name, df)` — Upload a CSV to Supabase table
- `download_raw_table(table_name)` → DataFrame
- `download_all_raw_to_dir(directory)` — Download all raw tables as CSVs to a local directory
- `delete_all_raw_data()` — Truncate all raw tables
- `get_raw_row_counts()` → dict of table names to row counts

## Migrations

Migration files are in `backend/db/migrations/`. Run them via:

```bash
cd backend
python -m db.setup
```

Or execute each SQL file manually in the Supabase SQL Editor.

### Migration Files

#### `001_init.sql` — Core Tables

Creates the foundational tables:
- `pipeline_runs` — Pipeline execution metadata (id, status, timestamps, agent_summary, llm_decisions_log)
- `kpi_snapshots` — KPI results per run
- `forecast_snapshots` — Forecast results per run
- `insight_snapshots` — Business insights per run
- `hypothesis_snapshots` — Statistical test results per run
- `action_plan_snapshots` — Prioritized action items per run
- `cleaned_datasets` — Metadata about cleaned tables (table_name, row_count, column_count, preview_rows, column_stats)
- `featured_datasets` — Metadata about feature-engineered tables
- `cleaning_reports` — Cleaning pipeline reports
- `feature_reports` — Feature engineering reports
- `prescription_statuses` — Status tracking for action items

Also creates the `pipeline-artifacts` storage bucket.

#### `002_disable_rls.sql` — Disable Row-Level Security

Disables RLS on all tables for simplified access (uses service role key).

#### `003_storage_policies.sql` — Storage Bucket Policies

Sets up public read/write policies for the `pipeline-artifacts` bucket.

#### `004_ai_analysis.sql` — AI Analysis Cache

Creates `ai_analysis_snapshots` and `comparison_ai_snapshots` tables for caching LLM-generated analyses.

#### `005_raw_datasets.sql` — Raw Data Tables

Creates the 12 raw data tables:
- `raw_customers`, `raw_products`, `raw_inventory`
- `raw_transactions`, `raw_transactions_with_session`, `raw_payments`
- `raw_marketing`, `raw_campaign_performance`
- `raw_sessions`, `raw_events`, `raw_web_analytics`
- `raw_funnel_summary`

#### `006_rag_pgvector.sql` — Vector Search

Enables the `pgvector` extension and creates:
- `rag_documents` — Stores document chunks with embedding vectors (content, metadata, embedding, source, source_id)
- `chat_messages` — Chat history (session_id, role, content, created_at)

#### `007_pipeline_current_agent.sql` — Pipeline Progress

Adds `current_agent` column to `pipeline_runs` for tracking which agent is currently executing.

## Key Tables Summary

| Table | Purpose |
|---|---|
| `pipeline_runs` | Pipeline execution records (status, duration, agent summaries) |
| `kpi_snapshots` | KPI cards per run (JSONB data) |
| `forecast_snapshots` | ML forecast results per run |
| `insight_snapshots` | Business insights per run |
| `hypothesis_snapshots` | Statistical test results per run |
| `action_plan_snapshots` | Prioritized action items per run |
| `ai_analysis_snapshots` | Cached LLM analyses per run |
| `comparison_ai_snapshots` | Cached run-to-run comparison analyses |
| `cleaned_datasets` | Cleaned data metadata + preview |
| `featured_datasets` | Feature-engineered data metadata + preview |
| `cleaning_reports` | Cleaning pipeline reports |
| `feature_reports` | Feature engineering reports |
| `prescription_statuses` | Action item status tracking |
| `raw_customers`, `raw_products`, ... | 12 raw data source tables |
| `rag_documents` | pgvector embeddings for similarity search |
| `chat_messages` | Chat conversation history |

## Storage Bucket

The `pipeline-artifacts` bucket stores full CSV files from pipeline runs. Files are organized by run ID:

```
pipeline-artifacts/
├── <run_id>/
│   ├── cleaned/
│   │   ├── customers_cleaned.csv
│   │   ├── transactions_cleaned.csv
│   │   └── ...
│   └── featured/
│       ├── customers_features.csv
│       └── ...
```

Temporary signed URLs are generated via `get_signed_url()` for downloading files.
