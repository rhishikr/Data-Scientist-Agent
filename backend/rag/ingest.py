# backend/rag/ingest.py
from pathlib import Path
from typing import Dict, Any

from .config import load_config
from .etl import build_documents_from_csv_dir
from .store_faiss import FaissStore


def rebuild_index(base_dir: Path) -> Dict[str, Any]:
    """
    POC ingestion: rebuild embeddings + FAISS index from scratch.
    Fast to implement, reliable for demos.
    """
    cfg = load_config(base_dir)

    docs = build_documents_from_csv_dir(
        data_dir=cfg.data_dir,
        max_sample_rows=100,   # tune for speed
        max_cols_per_row=20
    )

    store = FaissStore(cfg)
    vs = store.build_from_docs(docs)
    store.save(vs)

    return {
        "status": "rebuilt",
        "docs_indexed": len(docs),
        "data_dir": str(cfg.data_dir),
        "vector_dir": str(cfg.vector_dir),
        "llm_model": cfg.llm_model,
        "embed_model": cfg.embed_model,
        "top_k": cfg.top_k,
    }
