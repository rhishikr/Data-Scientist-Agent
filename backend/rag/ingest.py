# backend/rag/ingest.py
"""
Ingestion: rebuild the pgvector index from Supabase data + pipeline snapshots.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .config import load_config
from .store_pgvector import PgVectorStore
from .etl import (
    build_table_profile_documents,
    build_insight_documents,
    build_hypothesis_documents,
    build_kpi_documents,
)

logger = logging.getLogger(__name__)


def rebuild_index(base_dir: Path, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Rebuild the pgvector index from scratch:
      1. Table profiles + sample rows from cleaned datasets
      2. Insights from latest insight_snapshots
      3. Hypothesis results from latest hypothesis_snapshots
      4. KPI cards from latest kpi_snapshots

    Args:
        base_dir: Project base directory for config loading.
        run_id: Optional pipeline run ID. If provided, uses cleaned data
                from that run. If None, uses the latest completed run.

    Each source category is fully replaced (delete + insert).
    """
    cfg = load_config(base_dir)
    store = PgVectorStore(cfg)

    # Build all document types (all read from Supabase)
    table_docs = build_table_profile_documents(run_id=run_id)
    insight_docs = build_insight_documents()
    hypothesis_docs = build_hypothesis_documents()
    kpi_docs = build_kpi_documents()

    all_docs = table_docs + insight_docs + hypothesis_docs + kpi_docs

    if all_docs:
        count = store.upsert_documents(all_docs)
    else:
        count = 0
        logger.warning("No documents to index")

    summary = {
        "status": "rebuilt",
        "docs_indexed": count,
        "breakdown": {
            "table_profiles_and_samples": len(table_docs),
            "insights": len(insight_docs),
            "hypothesis_results": len(hypothesis_docs),
            "kpi_cards": len(kpi_docs),
        },
        "llm_model": cfg.llm_model,
        "embed_model": cfg.embed_model,
        "top_k": cfg.top_k,
    }

    logger.info("Index rebuilt: %s", summary)
    return summary
