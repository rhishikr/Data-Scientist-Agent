from __future__ import annotations

import os
import time
from typing import TypeVar, Callable

from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    """Return a Supabase client, creating one if needed."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


def reset_client() -> None:
    """Force a fresh client on next call (used after connection errors)."""
    global _client
    _client = None


T = TypeVar("T")


def with_retry(fn: Callable[[], T], retries: int = 2) -> T:
    """Execute a Supabase operation with retry on transient connection errors."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            is_transient = "ReadError" in type(e).__name__ or "10035" in str(e)
            if is_transient and attempt < retries:
                reset_client()
                time.sleep(0.5)
                continue
            raise
