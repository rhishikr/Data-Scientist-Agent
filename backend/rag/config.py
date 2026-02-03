# backend/rag/config.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class RagConfig:
    # Base paths
    base_dir: Path          # backend/
    data_dir: Path          # backend/data/
    artifacts_dir: Path     # backend/rag_artifacts/
    vector_dir: Path        # backend/rag_artifacts/vectorstore/

    # Models
    llm_model: str
    embed_model: str

    # Retrieval
    top_k: int


def load_config(base_dir: Path) -> RagConfig:
    """
    Central config for RAG so ingestion + chat always agree on:
    - where data lives
    - where FAISS index is stored
    - model names
    """
    data_dir = Path(os.getenv("RAG_DATA_DIR", base_dir / "data"))
    artifacts_dir = Path(os.getenv("RAG_ARTIFACTS_DIR", base_dir / "rag_artifacts"))
    vector_dir = artifacts_dir / "vectorstore"

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    vector_dir.mkdir(parents=True, exist_ok=True)

    return RagConfig(
        base_dir=base_dir,
        data_dir=data_dir,
        artifacts_dir=artifacts_dir,
        vector_dir=vector_dir,
        llm_model=os.getenv("RAG_LLM_MODEL", "gpt-4o-mini"),
        embed_model=os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small"),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )
