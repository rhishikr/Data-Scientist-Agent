"""
One-time migration: upload all CSV files from data/raw/ into Supabase raw_ tables.

Usage:
    cd backend
    python scripts/migrate_raw_to_supabase.py
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Ensure backend/ is on sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pandas as pd
from db.raw_store import replace_raw_table, TABLE_MAP


RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def main():
    if not RAW_DIR.exists():
        print(f"ERROR: Raw data directory not found: {RAW_DIR}")
        sys.exit(1)

    print(f"Migrating CSVs from {RAW_DIR} to Supabase...\n")

    for csv_name in TABLE_MAP:
        csv_path = RAW_DIR / csv_name
        if not csv_path.exists():
            print(f"  SKIP  {csv_name} (file not found)")
            continue

        df = pd.read_csv(csv_path)
        rows = replace_raw_table(csv_name, df)
        print(f"  OK    {csv_name}: {rows} rows uploaded")

    print("\nMigration complete!")


if __name__ == "__main__":
    main()
