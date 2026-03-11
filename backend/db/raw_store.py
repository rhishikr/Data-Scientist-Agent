"""
Raw data storage layer for Supabase PostgreSQL tables.

Handles CRUD operations for the 12 raw retail data tables that serve as the
source of truth (replacing local CSV files in data/raw/).
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .supabase_client import get_supabase, with_retry

# ---------------------------------------------------------------------------
# Table mapping: CSV filename -> Supabase table name
# ---------------------------------------------------------------------------

TABLE_MAP: Dict[str, str] = {
    "customers.csv": "raw_customers",
    "products.csv": "raw_products",
    "inventory.csv": "raw_inventory",
    "transactions.csv": "raw_transactions",
    "transactions_with_session.csv": "raw_transactions_with_session",
    "payments.csv": "raw_payments",
    "marketing.csv": "raw_marketing",
    "campaign_performance.csv": "raw_campaign_performance",
    "sessions.csv": "raw_sessions",
    "events.csv": "raw_events",
    "web_analytics.csv": "raw_web_analytics",
    "funnel_summary.csv": "raw_funnel_summary",
}

# Columns to exclude when returning DataFrames (internal DB columns)
_INTERNAL_COLS = {"id", "created_at"}

BATCH_SIZE = 500
PAGE_SIZE = 1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_table(table_key: str) -> str:
    """Resolve a table key (e.g. 'customers.csv' or 'raw_customers') to the DB table name."""
    if table_key in TABLE_MAP:
        return TABLE_MAP[table_key]
    if table_key in TABLE_MAP.values():
        return table_key
    raise ValueError(
        f"Unknown table key: {table_key}. "
        f"Valid keys: {list(TABLE_MAP.keys())}"
    )


def _sanitize_for_insert(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a DataFrame to a list of dicts suitable for Supabase insert.
    Replaces NaN/Inf with None (→ SQL NULL).
    """
    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if k in _INTERNAL_COLS:
                continue
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean[k] = None
            elif pd.isna(v):
                clean[k] = None
            else:
                clean[k] = v
            # Convert numpy types to native Python
            if hasattr(clean.get(k), "item"):
                clean[k] = clean[k].item()
        records.append(clean)
    return records


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def replace_raw_table(table_key: str, df: pd.DataFrame) -> int:
    """Truncate the table and bulk-insert the DataFrame.
    Used by generate_synthetic_data.py and inventory full-overwrite.
    Returns number of rows inserted.
    """
    table = _resolve_table(table_key)
    sb = get_supabase()

    # Delete all existing rows
    with_retry(lambda: sb.table(table).delete().neq("id", -1).execute())

    if df.empty:
        return 0

    records = _sanitize_for_insert(df)
    inserted = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        with_retry(lambda b=batch: sb.table(table).insert(b).execute())
        inserted += len(batch)
    return inserted


def append_raw_rows(table_key: str, df: pd.DataFrame) -> int:
    """Append new rows to the table.
    Used by simulate_update.py to add incremental data.
    Returns number of rows inserted.
    """
    if df.empty:
        return 0

    table = _resolve_table(table_key)
    sb = get_supabase()
    records = _sanitize_for_insert(df)
    inserted = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        with_retry(lambda b=batch: sb.table(table).insert(b).execute())
        inserted += len(batch)
    return inserted


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def read_raw_table(table_key: str) -> pd.DataFrame:
    """Read the full raw table into a DataFrame.
    Uses pagination to handle Supabase default row limits.
    Drops internal columns (id, created_at) so the result matches original CSV schema.
    """
    table = _resolve_table(table_key)
    sb = get_supabase()

    all_rows: List[Dict] = []
    offset = 0
    while True:
        def _query(o=offset):
            return (
                sb.table(table)
                .select("*")
                .range(o, o + PAGE_SIZE - 1)
                .execute()
            )
        result = with_retry(_query)
        if not result.data:
            break
        all_rows.extend(result.data)
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    # Drop internal columns
    df = df.drop(columns=[c for c in _INTERNAL_COLS if c in df.columns], errors="ignore")
    return df


def get_max_id(table_key: str, column: str, prefix: str) -> int:
    """Get the maximum numeric ID from an ID column like 'CUST1234'.
    Extracts digits and returns the max value. Returns 0 if table is empty.
    """
    table = _resolve_table(table_key)
    sb = get_supabase()

    # Fetch just the ID column
    all_ids: List[str] = []
    offset = 0
    while True:
        def _query(o=offset):
            return (
                sb.table(table)
                .select(column)
                .range(o, o + PAGE_SIZE - 1)
                .execute()
            )
        result = with_retry(_query)
        if not result.data:
            break
        for row in result.data:
            val = row.get(column)
            if val is not None:
                all_ids.append(str(val))
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not all_ids:
        return 0

    max_num = 0
    for id_val in all_ids:
        match = re.search(r"(\d+)", id_val)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return max_num


def get_latest_date(table_key: str, column: str) -> datetime:
    """Get the latest date from a date/datetime column.
    Returns the max date, or a default if the table is empty.
    """
    table = _resolve_table(table_key)
    sb = get_supabase()

    all_dates: List[str] = []
    offset = 0
    while True:
        def _query(o=offset):
            return (
                sb.table(table)
                .select(column)
                .range(o, o + PAGE_SIZE - 1)
                .execute()
            )
        result = with_retry(_query)
        if not result.data:
            break
        for row in result.data:
            val = row.get(column)
            if val is not None:
                all_dates.append(str(val))
        if len(result.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not all_dates:
        return datetime(2026, 2, 15)

    dates = pd.to_datetime(pd.Series(all_dates), errors="coerce").dropna()
    if len(dates) == 0:
        return datetime(2026, 2, 15)
    return dates.max().to_pydatetime()


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------

def download_all_raw_to_dir(target_dir: str) -> Dict[str, Path]:
    """Download all 12 raw tables as CSV files into target_dir.
    Returns mapping of CSV filename -> file path.
    Used as a bridge for subprocess-based pipeline agents.
    """
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    result = {}
    for csv_name, table_name in TABLE_MAP.items():
        df = read_raw_table(csv_name)
        file_path = target / csv_name
        df.to_csv(file_path, index=False)
        result[csv_name] = file_path
    return result


def delete_all_raw_data() -> Dict[str, int]:
    """Truncate all 12 raw data tables.
    Returns dict of table_key -> rows deleted.
    """
    sb = get_supabase()
    deleted = {}
    for csv_name, table_name in TABLE_MAP.items():
        # Get count before delete
        def _count(t=table_name):
            return sb.table(t).select("id", count="exact").execute()
        result = with_retry(_count)
        count = result.count if result.count is not None else 0

        # Delete all rows
        with_retry(lambda t=table_name: sb.table(t).delete().neq("id", -1).execute())
        deleted[csv_name] = count
    return deleted


def get_raw_data_stats() -> Dict[str, Any]:
    """Get row counts for all raw tables. Used by the status API endpoint."""
    sb = get_supabase()
    stats = {}
    total = 0
    for csv_name, table_name in TABLE_MAP.items():
        def _count(t=table_name):
            return sb.table(t).select("id", count="exact").execute()
        result = with_retry(_count)
        count = result.count if result.count is not None else 0
        # Use a friendly name: "customers.csv" -> "customers"
        friendly = csv_name.replace(".csv", "")
        stats[friendly] = count
        total += count
    stats["_total"] = total
    return stats
