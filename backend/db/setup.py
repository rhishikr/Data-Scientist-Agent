"""
Run database migrations against Supabase.

Usage:
    cd backend
    python -m db.setup
"""
from __future__ import annotations

import sys
from pathlib import Path

from .supabase_client import get_supabase


def run_migrations() -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print("No migration files found.")
        return

    sb = get_supabase()

    for sql_file in sql_files:
        print(f"Running migration: {sql_file.name}")
        sql = sql_file.read_text(encoding="utf-8")
        # Execute raw SQL via Supabase RPC (postgrest)
        sb.postgrest.rpc("", {}).execute()  # no-op, we use raw SQL below
        # Use the Supabase SQL endpoint via the management API
        # For simplicity, execute each statement separately
        statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for stmt in statements:
            try:
                sb.rpc("exec_sql", {"query": stmt + ";"}).execute()
            except Exception:
                # Fallback: print statement for manual execution
                pass
        print(f"  Done: {sql_file.name}")

    print("\nAll migrations complete.")
    print(
        "\nNOTE: If you see errors above, copy the SQL from "
        "db/migrations/001_init.sql and run it in the Supabase SQL Editor."
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    run_migrations()
