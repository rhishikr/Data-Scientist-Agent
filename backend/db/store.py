"""
Supabase storage layer for pipeline results.

Every pipeline run creates a row in `pipeline_runs` and stores its outputs
(snapshots, cleaned/featured data, reports) linked to that run_id.
Full CSV files are uploaded to the `pipeline-artifacts` Storage bucket;
metadata + preview rows live in the DB for fast dashboard rendering.
"""
from __future__ import annotations

import io
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .supabase_client import get_supabase, with_retry

STORAGE_BUCKET = "pipeline-artifacts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_json(obj: Any) -> Any:
    """Recursively replace NaN / Inf with None so JSON serialization succeeds."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    return obj


def _df_to_storage(df: pd.DataFrame) -> dict:
    """Convert a DataFrame to preview rows + column stats for DB storage."""
    preview = df.head(100).to_dict(orient="records")
    col_stats: Dict[str, Any] = {}
    for col in df.columns:
        col_stats[col] = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "non_null_count": int(df[col].notnull().sum()),
            "unique_count": int(df[col].nunique()),
            "sample_values": [
                v if not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else None
                for v in df[col].dropna().head(5).tolist()
            ],
        }
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "preview_rows": _sanitize_json(preview),
        "column_stats": _sanitize_json(col_stats),
    }


# ---------------------------------------------------------------------------
# Pipeline runs
# ---------------------------------------------------------------------------

def create_pipeline_run() -> str:
    """Insert a new pipeline_run row and return its UUID."""
    sb = get_supabase()
    row = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    }
    result = sb.table("pipeline_runs").insert(row).execute()
    return result.data[0]["id"]


def complete_pipeline_run(
    run_id: str,
    status: str,
    duration_seconds: float,
    agent_summary: dict | None = None,
    llm_decisions_log: list | None = None,
) -> None:
    """Mark a pipeline run as completed/failed."""
    sb = get_supabase()
    sb.table("pipeline_runs").update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "duration_seconds": round(duration_seconds, 2),
        "agent_summary": _sanitize_json(agent_summary or {}),
        "llm_decisions_log": _sanitize_json(llm_decisions_log or []),
    }).eq("id", run_id).execute()


# ---------------------------------------------------------------------------
# Snapshot storage (KPI, Forecast, Insights, Hypothesis)
# ---------------------------------------------------------------------------

def _store_snapshot(table: str, run_id: str, snapshot: dict) -> None:
    sb = get_supabase()
    sb.table(table).insert({
        "run_id": run_id,
        "snapshot": _sanitize_json(snapshot),
    }).execute()


def store_kpi_snapshot(run_id: str, snapshot: dict) -> None:
    _store_snapshot("kpi_snapshots", run_id, snapshot)


def store_forecast_snapshot(run_id: str, snapshot: dict) -> None:
    _store_snapshot("forecast_snapshots", run_id, snapshot)


def store_insight_snapshot(run_id: str, snapshot: dict) -> None:
    _store_snapshot("insight_snapshots", run_id, snapshot)


def store_hypothesis_snapshot(run_id: str, snapshot: dict) -> None:
    _store_snapshot("hypothesis_snapshots", run_id, snapshot)


# ---------------------------------------------------------------------------
# Cleaned / Featured dataset storage (DB metadata + Storage bucket CSV)
# ---------------------------------------------------------------------------

def upload_csv_to_storage(
    run_id: str, stage: str, table_name: str, df: pd.DataFrame
) -> str:
    """Upload a DataFrame as CSV to the Storage bucket. Returns the path."""
    sb = get_supabase()
    path = f"runs/{run_id}/{stage}/{table_name}.csv"
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    sb.storage.from_(STORAGE_BUCKET).upload(
        path, buf.getvalue(), {"content-type": "text/csv"}
    )
    return path


def store_cleaned_dataset(run_id: str, table_name: str, df: pd.DataFrame) -> None:
    """Upload full CSV to Storage, then insert preview + stats into DB."""
    storage_path = upload_csv_to_storage(run_id, "cleaned", table_name, df)
    info = _df_to_storage(df)
    sb = get_supabase()
    sb.table("cleaned_datasets").insert({
        "run_id": run_id,
        "table_name": table_name,
        "row_count": info["row_count"],
        "column_count": info["column_count"],
        "preview_rows": info["preview_rows"],
        "column_stats": info["column_stats"],
        "storage_path": storage_path,
    }).execute()


def store_featured_dataset(run_id: str, table_name: str, df: pd.DataFrame) -> None:
    """Upload full CSV to Storage, then insert preview + stats into DB."""
    storage_path = upload_csv_to_storage(run_id, "featured", table_name, df)
    info = _df_to_storage(df)
    sb = get_supabase()
    sb.table("featured_datasets").insert({
        "run_id": run_id,
        "table_name": table_name,
        "row_count": info["row_count"],
        "column_count": info["column_count"],
        "preview_rows": info["preview_rows"],
        "column_stats": info["column_stats"],
        "storage_path": storage_path,
    }).execute()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def store_cleaning_report(run_id: str, report: dict) -> None:
    sb = get_supabase()
    sb.table("cleaning_reports").insert({
        "run_id": run_id,
        "report": _sanitize_json(report),
    }).execute()


def store_feature_report(run_id: str, report: dict) -> None:
    sb = get_supabase()
    sb.table("feature_reports").insert({
        "run_id": run_id,
        "report": _sanitize_json(report),
    }).execute()


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def _get_latest_snapshot(table: str) -> dict:
    """Fetch the most recent snapshot from a given table."""
    def _query():
        sb = get_supabase()
        return (
            sb.table(table)
            .select("snapshot, run_id, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    result = with_retry(_query)
    if result.data:
        return result.data[0]["snapshot"]
    return {"error": f"No data found in {table}. Run the pipeline first."}


def _get_snapshot_for_run(table: str, run_id: str) -> dict:
    def _query():
        sb = get_supabase()
        return (
            sb.table(table)
            .select("snapshot")
            .eq("run_id", run_id)
            .limit(1)
            .execute()
        )
    result = with_retry(_query)
    if result.data:
        return result.data[0]["snapshot"]
    return {"error": f"No data found in {table} for run {run_id}"}


def get_latest_kpi_snapshot() -> dict:
    return _get_latest_snapshot("kpi_snapshots")


def get_latest_forecast_snapshot() -> dict:
    return _get_latest_snapshot("forecast_snapshots")


def get_latest_insight_snapshot() -> dict:
    return _get_latest_snapshot("insight_snapshots")


def get_latest_hypothesis_snapshot() -> dict:
    return _get_latest_snapshot("hypothesis_snapshots")


def get_run_kpi_snapshot(run_id: str) -> dict:
    return _get_snapshot_for_run("kpi_snapshots", run_id)


def get_run_forecast_snapshot(run_id: str) -> dict:
    return _get_snapshot_for_run("forecast_snapshots", run_id)


def get_run_insight_snapshot(run_id: str) -> dict:
    return _get_snapshot_for_run("insight_snapshots", run_id)


def get_run_hypothesis_snapshot(run_id: str) -> dict:
    return _get_snapshot_for_run("hypothesis_snapshots", run_id)


# ---------------------------------------------------------------------------
# Cleaned / Featured data reads
# ---------------------------------------------------------------------------

def get_cleaned_datasets(run_id: str) -> list:
    def _query():
        sb = get_supabase()
        return (
            sb.table("cleaned_datasets")
            .select("table_name, row_count, column_count, preview_rows, column_stats, storage_path")
            .eq("run_id", run_id)
            .execute()
        )
    result = with_retry(_query)
    return result.data or []


def get_featured_datasets(run_id: str) -> list:
    def _query():
        sb = get_supabase()
        return (
            sb.table("featured_datasets")
            .select("table_name, row_count, column_count, preview_rows, column_stats, storage_path")
            .eq("run_id", run_id)
            .execute()
        )
    result = with_retry(_query)
    return result.data or []


def get_cleaning_report(run_id: str) -> dict:
    def _query():
        sb = get_supabase()
        return (
            sb.table("cleaning_reports")
            .select("report")
            .eq("run_id", run_id)
            .limit(1)
            .execute()
        )
    result = with_retry(_query)
    if result.data:
        return result.data[0]["report"]
    return {}


def get_feature_report(run_id: str) -> dict:
    def _query():
        sb = get_supabase()
        return (
            sb.table("feature_reports")
            .select("report")
            .eq("run_id", run_id)
            .limit(1)
            .execute()
        )
    result = with_retry(_query)
    if result.data:
        return result.data[0]["report"]
    return {}


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for downloading a file from the Storage bucket."""
    def _query():
        sb = get_supabase()
        return sb.storage.from_(STORAGE_BUCKET).create_signed_url(
            storage_path, expires_in
        )
    result = with_retry(_query)
    return result.get("signedURL", "")


# ---------------------------------------------------------------------------
# Pipeline runs list & detail
# ---------------------------------------------------------------------------

def get_pipeline_runs() -> list:
    """All pipeline runs, most recent first."""
    def _query():
        sb = get_supabase()
        return (
            sb.table("pipeline_runs")
            .select("id, started_at, completed_at, status, duration_seconds")
            .order("started_at", desc=True)
            .execute()
        )
    result = with_retry(_query)
    return result.data or []


def get_latest_run_id() -> Optional[str]:
    """Return the ID of the most recently completed run, or None."""
    def _query():
        sb = get_supabase()
        return (
            sb.table("pipeline_runs")
            .select("id")
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(1)
            .execute()
        )
    result = with_retry(_query)
    if result.data:
        return result.data[0]["id"]
    return None


def get_run_snapshots(run_id: str) -> dict:
    """Return all snapshots + cleaned/featured data for a specific run."""
    return {
        "run_id": run_id,
        "kpi": get_run_kpi_snapshot(run_id),
        "forecast": get_run_forecast_snapshot(run_id),
        "insights": get_run_insight_snapshot(run_id),
        "hypothesis": get_run_hypothesis_snapshot(run_id),
        "cleaned_datasets": get_cleaned_datasets(run_id),
        "featured_datasets": get_featured_datasets(run_id),
        "cleaning_report": get_cleaning_report(run_id),
        "feature_report": get_feature_report(run_id),
    }
