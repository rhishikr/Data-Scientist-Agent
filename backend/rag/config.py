# backend/rag/config.py
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class RagConfig:
    # Base paths
    base_dir: Path          # backend/
    data_dir: Path          # backend/data/
    artifacts_dir: Path     # backend/rag_artifacts/ (temp files if needed)

    # Database
    db_url: str             # Direct PostgreSQL connection string for Supabase

    # Models
    llm_model: str
    embed_model: str

    # Retrieval
    top_k: int


def load_config(base_dir: Path) -> RagConfig:
    """
    Central config for RAG — ingestion, chat, and SQL agent all use this.
    """
    data_dir = Path(os.getenv("RAG_DATA_DIR", base_dir / "data"))
    artifacts_dir = Path(os.getenv("RAG_ARTIFACTS_DIR", base_dir / "rag_artifacts"))

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    db_url = os.getenv("SUPABASE_DB_URL", "")
    if not db_url:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. "
            "Get it from Supabase Dashboard > Settings > Database > Connection string (Transaction pooler, port 6543)."
        )

    return RagConfig(
        base_dir=base_dir,
        data_dir=data_dir,
        artifacts_dir=artifacts_dir,
        db_url=db_url,
        llm_model=os.getenv("RAG_LLM_MODEL", "gpt-4o-mini"),
        embed_model=os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small"),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )
