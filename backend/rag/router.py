# backend/rag/router.py
"""
Query type definitions for the RAG service.

The assistant uses a two-path architecture:
  - "snapshot": instant lookup of pre-computed KPI / forecast / health-score metrics
  - "retrieval": pgvector semantic search + LLM synthesis from cleaned pipeline data
"""
from typing import Literal

QueryType = Literal["snapshot", "retrieval"]
